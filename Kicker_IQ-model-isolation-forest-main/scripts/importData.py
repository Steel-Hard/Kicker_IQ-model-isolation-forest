import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
import sys

# Configurações via ambiente
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://postgres:123@localhost:5432/kicker_iq_model")
XLSX_PATH = os.getenv("XLSX_PATH", "../data/players.xlsx")

def nan_to_none(value):
    """Converte NaN/NaT do pandas para None (NULL no postgres)."""
    if pd.isna(value):
        return None
    return value

def time_to_float(value):
    """
    Converte valor de tempo para fração decimal do dia (formato Excel).
    """
    if pd.isna(value):
        return None
    if hasattr(value, 'hour'):
        return (value.hour * 3600 + value.minute * 60 + value.second) / 86400
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def create_schema(cur):
    """Cria a estrutura de tabelas necessária com suporte a IDs grandes (BIGINT)."""
    print("Verificando/Criando esquema do banco de dados...")
    
    # Tabela principal utilizada pelo backend para listagem
    # Usamos BIGINT para o Athlete ID para evitar erro de "inteiro fora do intervalo"
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.players (
            "Athlete ID" BIGINT PRIMARY KEY,
            "Name" TEXT,
            "Position" TEXT,
            "Groups" TEXT,
            "Top Speed" FLOAT,
            "Sprint Distance" FLOAT,
            "Start Date" DATE,
            "Start Time" TIME,
            "Duration (mins)" FLOAT,
            "Distance (m)" FLOAT,
            "Avg Speed (kph)" FLOAT
        );
        
        -- Garante que se a tabela já existir com INTEGER, ela seja atualizada para BIGINT
        ALTER TABLE public.players ALTER COLUMN "Athlete ID" TYPE BIGINT;
    """)

    # Tabelas utilizadas pelo microserviço de IA
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.athlete (
            id BIGINT PRIMARY KEY,
            position TEXT,
            grp TEXT
        );
        ALTER TABLE public.athlete ALTER COLUMN id TYPE BIGINT;
        
        CREATE TABLE IF NOT EXISTS public.match (
            id SERIAL PRIMARY KEY,
            match_date DATE,
            start_time TIME,
            week_start_date DATE,
            month_start_date DATE,
            UNIQUE(match_date, start_time)
        );
        
        CREATE TABLE IF NOT EXISTS public.performance_segment (
            athlete_id BIGINT REFERENCES public.athlete(id),
            match_id INTEGER REFERENCES public.match(id),
            segment_name TEXT,
            start_time_s FLOAT,
            end_time_s FLOAT,
            duration_mins FLOAT,
            session_load FLOAT,
            workload FLOAT,
            workload_volume FLOAT,
            workload_intensity FLOAT,
            distance_m FLOAT,
            metres_per_minute FLOAT,
            high_intensity_running_m FLOAT,
            no_high_intensity_events FLOAT,
            sprint_distance_m FLOAT,
            no_sprints FLOAT,
            raw_top_speed_kph FLOAT,
            top_speed_kph FLOAT,
            avg_speed_kph FLOAT,
            accelerations FLOAT,
            decelerations FLOAT,
            pct_max_speed FLOAT,
            pct_raw_max_speed FLOAT,
            speed_90pct_events FLOAT,
            speed_90pct_distance_m FLOAT,
            speed_90pct_duration_secs FLOAT,
            raw_speed_90pct_events FLOAT,
            raw_speed_90pct_distance_m FLOAT,
            raw_speed_90pct_duration_secs FLOAT,
            PRIMARY KEY (athlete_id, match_id, segment_name)
        );
        ALTER TABLE public.performance_segment ALTER COLUMN athlete_id TYPE BIGINT;
    """)

def main():
    if not os.path.exists(XLSX_PATH):
        print(f"Erro: Arquivo {XLSX_PATH} não encontrado.")
        sys.exit(1)

    print(f"Lendo {XLSX_PATH}...")
    df = pd.read_excel(XLSX_PATH)

    # Conversão de colunas de tempo
    for col in ["Start Time (s)", "End Time (s)"]:
        if col in df.columns:
            df[col] = df[col].apply(time_to_float)

    print(f"  {len(df)} linhas carregadas.")

    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                create_schema(cur)
                conn.commit()

                # 1. Popular Tabela public.players (Backend)
                print("\nPopulando public.players...")
                # Tenta encontrar a coluna de nome
                name_col = next((c for col in ["Name", "Full Name", "Athlete Name"] for c in df.columns if col.lower() in c.lower()), None)
                
                player_cols = ["Athlete ID", "Athlete Position", "Athlete Groups", "Top Speed (kph)", "Sprint Distance (m)", "Start Date", "Start Time", "Duration (mins)", "Distance (m)", "Avg Speed (kph)"]
                if name_col:
                    player_cols.insert(1, name_col)
                
                players_df = df[player_cols].drop_duplicates(subset=["Athlete ID"])
                
                for _, row in players_df.iterrows():
                    cur.execute("""
                        INSERT INTO public.players (
                            "Athlete ID", "Name", "Position", "Groups", "Top Speed", "Sprint Distance",
                            "Start Date", "Start Time", "Duration (mins)", "Distance (m)", "Avg Speed (kph)"
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT ("Athlete ID") DO UPDATE SET
                            "Name" = EXCLUDED."Name",
                            "Position" = EXCLUDED."Position",
                            "Groups" = EXCLUDED."Groups",
                            "Top Speed" = EXCLUDED."Top Speed",
                            "Sprint Distance" = EXCLUDED."Sprint Distance",
                            "Start Date" = EXCLUDED."Start Date",
                            "Start Time" = EXCLUDED."Start Time",
                            "Duration (mins)" = EXCLUDED."Duration (mins)",
                            "Distance (m)" = EXCLUDED."Distance (m)",
                            "Avg Speed (kph)" = EXCLUDED."Avg Speed (kph)"
                    """, (
                        int(row["Athlete ID"]),
                        nan_to_none(row[name_col]) if name_col else "Atleta " + str(row["Athlete ID"]),
                        nan_to_none(row["Athlete Position"]),
                        nan_to_none(row["Athlete Groups"]),
                        nan_to_none(row["Top Speed (kph)"]),
                        nan_to_none(row["Sprint Distance (m)"]),
                        nan_to_none(row["Start Date"]),
                        nan_to_none(row["Start Time"]),
                        nan_to_none(row["Duration (mins)"]),
                        nan_to_none(row["Distance (m)"]),
                        nan_to_none(row["Avg Speed (kph)"])
                    ))
                print(f"  {len(players_df)} jogadores inseridos/atualizados em public.players.")

                # 2. Popular Tabela public.athlete (Microserviço)
                print("\nInserindo athletes (microserviço)...")
                athlete_data = df[["Athlete ID", "Athlete Position", "Athlete Groups"]].drop_duplicates(subset=["Athlete ID"])
                execute_values(cur, """
                    INSERT INTO public.athlete (id, position, grp)
                    VALUES %s ON CONFLICT (id) DO NOTHING
                """, [
                    (int(row[0]), nan_to_none(row[1]), nan_to_none(row[2]))
                    for row in athlete_data.values.tolist()
                ])

                # 3. Popular Tabela public.match
                print("\nInserindo matches...")
                match_data = df[["Start Date", "Start Time", "Week Start Date", "Month Start Date"]].drop_duplicates(subset=["Start Date", "Start Time"])
                execute_values(cur, """
                    INSERT INTO public.match (match_date, start_time, week_start_date, month_start_date)
                    VALUES %s ON CONFLICT (match_date, start_time) DO NOTHING
                """, [
                    (nan_to_none(row[0]), nan_to_none(row[1]), nan_to_none(row[2]), nan_to_none(row[3]))
                    for row in match_data.values.tolist()
                ])

                # Mapa de matches para performance_segment
                cur.execute("SELECT id, match_date, start_time FROM public.match")
                match_map = {(str(r[1]), str(r[2])): r[0] for r in cur.fetchall()}

                # 4. Popular Tabela public.performance_segment
                print("\nInserindo performance_segments...")
                segments = []
                for _, row in df.iterrows():
                    date_key = str(row["Start Date"].date())
                    time_key = str(row["Start Time"])
                    match_id = match_map.get((date_key, time_key))
                    if match_id:
                        segments.append((
                            int(row["Athlete ID"]), match_id, row["Segment Name"],
                            nan_to_none(row["Start Time (s)"]), nan_to_none(row["End Time (s)"]), nan_to_none(row["Duration (mins)"]),
                            nan_to_none(row["Session Load"]), nan_to_none(row["Workload"]), nan_to_none(row["Workload Volume"]),
                            nan_to_none(row["Workload Intensity"]), nan_to_none(row["Distance (m)"]), nan_to_none(row["Metres per Minute (m)"]),
                            nan_to_none(row["High Intensity Running (m)"]), nan_to_none(row["No. of High Intensity Events"]), nan_to_none(row["Sprint Distance (m)"]),
                            nan_to_none(row["No. of Sprints"]), nan_to_none(row["Raw Top Speed (kph)"]), nan_to_none(row["Top Speed (kph)"]),
                            nan_to_none(row["Avg Speed (kph)"]), nan_to_none(row["Accelerations"]), nan_to_none(row["Decelerations"]),
                            nan_to_none(row["Percentage of Max Speed"]), nan_to_none(row["Percentage of Raw Max Speed KPH"]),
                            nan_to_none(row["90% of Max Speed Events"]), nan_to_none(row["90% of Max Speed Distance (m)"]), nan_to_none(row["90% of Max Speed Duration (secs)"]),
                            nan_to_none(row["90% of Raw Max Speed Events"]), nan_to_none(row["90% of Raw Max Speed Distance (m)"]), nan_to_none(row["90% of Raw Max Speed Duration (secs)"])
                        ))

                execute_values(cur, """
                    INSERT INTO public.performance_segment (
                        athlete_id, match_id, segment_name, start_time_s, end_time_s, duration_mins,
                        session_load, workload, workload_volume, workload_intensity, distance_m, metres_per_minute,
                        high_intensity_running_m, no_high_intensity_events, sprint_distance_m, no_sprints,
                        raw_top_speed_kph, top_speed_kph, avg_speed_kph, accelerations, decelerations,
                        pct_max_speed, pct_raw_max_speed, speed_90pct_events, speed_90pct_distance_m, speed_90pct_duration_secs,
                        raw_speed_90pct_events, raw_speed_90pct_distance_m, raw_speed_90pct_duration_secs
                    ) VALUES %s ON CONFLICT (athlete_id, match_id, segment_name) DO NOTHING
                """, segments)

                conn.commit()
                print("\nSeed concluído com sucesso!")

    except Exception as e:
        print(f"\nErro durante a execução: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

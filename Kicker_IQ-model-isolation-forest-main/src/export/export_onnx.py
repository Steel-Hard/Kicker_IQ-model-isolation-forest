"""
export_onnx.py
==============
Treina um Isolation Forest por atleta usando os dados do banco PostgreSQL
e exporta cada modelo no formato ONNX + scaler_params.json.

Estrutura de saída:
    model/
    └── <athlete_id>/
        ├── isolation_forest.onnx
        └── scaler_params.json

Uso:
    python src/export/export_onnx.py
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
from sklearn.impute import KNNImputer
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

warnings.filterwarnings("ignore")
load_dotenv()

# ── Configurações ──────────────────────────────────────────────────────────────

DATABASE_URL  = os.getenv("DATABASE_URL", "postgres://postgres:123@localhost:5432/kicker_iq_model")
MODEL_DIR     = os.path.join(os.path.dirname(__file__), "..", "..", "model")
RANDOM_STATE  = 42
MIN_SESSIONS  = 8       # Mínimo de sessões para treinar o modelo de um atleta
TRAIN_RATIO   = 0.70    # 70% treino / 30% teste (split temporal)

# Features de performance utilizadas pelo modelo
PERF_FEATURES = [
    "distance_m",
    "high_intensity_running_m",
    "no_high_intensity_events",
    "sprint_distance_m",
    "no_sprints",
    "top_speed_kph",
    "avg_speed_kph",
    "accelerations",
    "decelerations",
]

# ── Funções auxiliares ─────────────────────────────────────────────────────────

def fetch_sessions(conn) -> pd.DataFrame:
    """Busca todas as sessões 'Whole Session' do banco de dados."""
    query = """
        SELECT
            ps.athlete_id                   AS "athlete_id",
            m.match_date                    AS "match_date",
            ps.distance_m                   AS "distance_m",
            ps.high_intensity_running_m     AS "high_intensity_running_m",
            ps.no_high_intensity_events     AS "no_high_intensity_events",
            ps.sprint_distance_m            AS "sprint_distance_m",
            ps.no_sprints                   AS "no_sprints",
            ps.top_speed_kph                AS "top_speed_kph",
            ps.avg_speed_kph                AS "avg_speed_kph",
            ps.accelerations                AS "accelerations",
            ps.decelerations                AS "decelerations"
        FROM performance_segment ps
        JOIN match m ON m.id = ps.match_id
        WHERE ps.segment_name = 'Whole Session'
        ORDER BY ps.athlete_id, m.match_date ASC
    """
    return pd.read_sql(query, conn)


def impute_and_clean(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """
    Trata nulos:
    - Colunas com > 80% nulos → removidas
    - Colunas com 20–80% nulos → KNN Imputer
    - Colunas com < 20% nulos → mediana por atleta
    """
    null_pct = df[features].isnull().mean()

    drop_cols = null_pct[null_pct > 0.80].index.tolist()
    features = [f for f in features if f not in drop_cols]
    df = df.drop(columns=drop_cols)

    low_null = null_pct[(null_pct > 0) & (null_pct <= 0.20)].index.tolist()
    low_null = [c for c in low_null if c in features]
    for col in low_null:
        df[col] = df.groupby("athlete_id")[col].transform(
            lambda x: x.fillna(x.median())
        )
        df[col] = df[col].fillna(df[col].median())

    mid_null = null_pct[(null_pct > 0.20) & (null_pct <= 0.80)].index.tolist()
    mid_null = [c for c in mid_null if c in features]
    if mid_null:
        imputer = KNNImputer(n_neighbors=5)
        df[mid_null] = imputer.fit_transform(df[mid_null])

    return df, features


def build_engineered_features(player_df: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """
    Engenharia de features sem leakage temporal:
    - Z-score com expanding mean/std usando shift(1)
    - Δ vs média rolling das 5 sessões anteriores (shift(1))
    Remove features com correlação > 0.95.
    """
    player_df = player_df.copy().reset_index(drop=True)
    new_features = []

    for feat in features:
        if feat not in player_df.columns:
            continue

        # Z-score sem leakage
        col_z = f"{feat}_zscore"
        def zscore_expanding(x):
            m = x.shift(1).expanding(min_periods=2).mean()
            s = x.shift(1).expanding(min_periods=2).std()
            return (x - m) / (s + 1e-9)
        player_df[col_z] = zscore_expanding(player_df[feat])
        new_features.append(col_z)

        # Δ vs rolling 5 sem leakage
        col_roll = f"{feat}_vs_roll5"
        roll_mean = player_df[feat].shift(1).rolling(5, min_periods=2).mean()
        player_df[col_roll] = (player_df[feat] - roll_mean) / (roll_mean.abs() + 1e-9)
        new_features.append(col_roll)

    player_df[new_features] = player_df[new_features].fillna(0)

    all_candidate = [f for f in features if f in player_df.columns] + new_features
    corr_matrix = player_df[all_candidate].corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop = [col for col in upper.columns if any(upper[col] > 0.95)]
    model_features = [f for f in all_candidate if f not in to_drop]

    return player_df, model_features


def adaptive_contamination(X_train_sc: np.ndarray) -> float:
    """Calcula o contamination adaptativo via percentil 10 do pre-treino."""
    iso_pre = IsolationForest(n_estimators=100, contamination=0.10, random_state=RANDOM_STATE)
    iso_pre.fit(X_train_sc)
    pre_scores = iso_pre.decision_function(X_train_sc)
    return float(np.clip(np.mean(pre_scores < np.percentile(pre_scores, 10)), 0.01, 0.40))


def train_isolation_forest(X_train_sc: np.ndarray, contamination: float) -> IsolationForest:
    """Treina o Isolation Forest com os parâmetros finais."""
    iso = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        max_features=0.8,
        bootstrap=True,
        random_state=RANDOM_STATE,
    )
    iso.fit(X_train_sc)
    return iso


def export_athlete_model(
    athlete_id: int,
    iso: IsolationForest,
    scaler: RobustScaler,
    model_features: list[str],
    n_features: int,
) -> None:
    """
    Exporta o modelo e o scaler para a pasta model/<athlete_id>/.

    Arquivos gerados:
    - isolation_forest.onnx
    - scaler_params.json
    """
    out_dir = os.path.join(MODEL_DIR, str(athlete_id))
    os.makedirs(out_dir, exist_ok=True)

    # ── ONNX ──────────────────────────────────────────────────────────────────
    # O skl2onnx exporta o IsolationForest diretamente.
    # A entrada já deve chegar normalizada (float32).
    initial_type = [("float_input", FloatTensorType([None, n_features]))]
    onnx_model = convert_sklearn(iso, initial_types=initial_type, target_opset=17)

    onnx_path = os.path.join(out_dir, "isolation_forest.onnx")
    with open(onnx_path, "wb") as f:
        f.write(onnx_model.SerializeToString())

    # ── scaler_params.json ────────────────────────────────────────────────────
    # Salva center_ (median) e scale_ do RobustScaler para que o model-service
    # possa normalizar os dados antes de chamar o ONNX.
    scaler_params = {
        "center": scaler.center_.tolist(),
        "scale": scaler.scale_.tolist(),
        "features": model_features,
    }
    scaler_path = os.path.join(out_dir, "scaler_params.json")
    with open(scaler_path, "w") as f:
        json.dump(scaler_params, f, indent=2)

    print(f"  ✅ [{athlete_id}] → {onnx_path}")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def main():
    print("🔌 Conectando ao banco de dados...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")
        sys.exit(1)

    print("📥 Buscando sessões (Whole Session)...")
    df = fetch_sessions(conn)
    conn.close()

    print(f"   → {len(df)} sessões | {df['athlete_id'].nunique()} atletas únicos\n")

    # Limpeza global de nulos
    df, active_features = impute_and_clean(df, PERF_FEATURES)

    athletes   = df["athlete_id"].unique()
    exported   = 0
    skipped    = 0
    failed     = 0

    for athlete_id in athletes:
        player_df = (
            df[df["athlete_id"] == athlete_id]
            .sort_values("match_date")
            .copy()
        )
        n = len(player_df)

        if n < MIN_SESSIONS:
            print(f"  ⚠️  [{athlete_id}] Pulado — apenas {n} sessão(ões) (mínimo: {MIN_SESSIONS})")
            skipped += 1
            continue

        try:
            # Engenharia de features por atleta (sem leakage)
            player_df, model_features = build_engineered_features(player_df, active_features)

            # Split temporal 70/30
            cut       = int(n * TRAIN_RATIO)
            train_df  = player_df.iloc[:cut]
            X_train   = train_df[model_features].values

            # Scaler (fit apenas no treino)
            scaler      = RobustScaler()
            X_train_sc  = scaler.fit_transform(X_train)

            # Contamination adaptativo + treino final
            contamination = adaptive_contamination(X_train_sc)
            iso           = train_isolation_forest(X_train_sc, contamination)

            # Exporta ONNX + scaler_params.json
            export_athlete_model(
                athlete_id=int(athlete_id),
                iso=iso,
                scaler=scaler,
                model_features=model_features,
                n_features=len(model_features),
            )
            exported += 1

        except Exception as e:
            print(f"  ❌ [{athlete_id}] Erro: {e}")
            failed += 1

    print(f"\n{'─' * 45}")
    print(f"  Exportados  : {exported}")
    print(f"  Pulados     : {skipped}  (dados insuficientes)")
    print(f"  Com erro    : {failed}")
    print(f"{'─' * 45}")
    print(f"  Modelos em  : {os.path.abspath(MODEL_DIR)}/")


if __name__ == "__main__":
    main()

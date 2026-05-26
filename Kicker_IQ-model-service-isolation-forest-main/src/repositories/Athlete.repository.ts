import db from "../db"
import SessionMetrics from "../types/SessionMetrics"

class AthleteRepository {
    /**
     * Retorna todas as sessões "Whole Session" de um atleta, ordenadas por data (ASC).
     * A ordem temporal é necessária para que o resultado final reflita o histórico
     * cronológico do atleta, assim como foi treinado.
     */
    public async selectSessionsPerAthlete(athleteId: number): Promise<SessionMetrics[]> {
        const query = `
            SELECT
                ps.distance_m                   AS "distanceM",
                ps.high_intensity_running_m     AS "highIntensityRunningM",
                ps.no_high_intensity_events     AS "highIntensityEvents",
                ps.sprint_distance_m            AS "sprintDistanceM",
                ps.no_sprints                   AS "numberOfSprints",
                ps.top_speed_kph                AS "topSpeedKph",
                ps.avg_speed_kph                AS "avgSpeedKph",
                ps.accelerations                AS "accelerations",
                ps.decelerations                AS "decelerations"
            FROM performance_segment ps
            JOIN match m ON m.id = ps.match_id
            WHERE ps.athlete_id = $1
              AND ps.segment_name = 'Whole Session'
            ORDER BY m.match_date ASC
        `
        const res = await db.query(query, [athleteId])
        return res.rows as SessionMetrics[]
    }

    /**
     * Retorna a última sessão "Whole Session" de um atleta.
     * Usada no endpoint /anomaly/last para análise da sessão mais recente.
     */
    public async selectLastSession(athleteId: number): Promise<SessionMetrics | null> {
        const query = `
            SELECT
                ps.distance_m                   AS "distanceM",
                ps.high_intensity_running_m     AS "highIntensityRunningM",
                ps.no_high_intensity_events     AS "highIntensityEvents",
                ps.sprint_distance_m            AS "sprintDistanceM",
                ps.no_sprints                   AS "numberOfSprints",
                ps.top_speed_kph                AS "topSpeedKph",
                ps.avg_speed_kph                AS "avgSpeedKph",
                ps.accelerations                AS "accelerations",
                ps.decelerations                AS "decelerations"
            FROM performance_segment ps
            JOIN match m ON m.id = ps.match_id
            WHERE ps.athlete_id = $1
              AND ps.segment_name = 'Whole Session'
            ORDER BY m.match_date DESC
            LIMIT 1
        `
        const res = await db.query(query, [athleteId])
        return res.rows[0] ?? null
    }

    public async selectAthlete(athleteId: number) {
        const query = `
            SELECT *
            FROM athlete
            WHERE id = $1
        `
        const res = await db.query(query, [athleteId])
        return res.rows[0]
    }
}

export default AthleteRepository

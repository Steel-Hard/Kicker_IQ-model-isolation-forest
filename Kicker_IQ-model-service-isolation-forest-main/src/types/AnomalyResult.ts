type AnomalyResult = {
    isAnomaly: boolean;
    anomalyScore: number;
    anomalyLabel: string;
    atypicalDirection: 'Acima do padrão' | 'Abaixo do padrão' | null;
};

export default AnomalyResult

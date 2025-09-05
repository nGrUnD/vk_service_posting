import React, { useEffect, useState } from "react";
import api from "../api/axios";

export default function PostedClipsCount({ workerpostId }) {
    const [count, setCount] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        const fetchCount = async () => {
            try {
                const res = await api.get(`/users/{user_id}/workerpost/${workerpostId}/posted_clips/count`);
                if (!cancelled) {
                    setCount(res.data.count);
                }
            } catch (e) {
                console.error("Ошибка при получении количества клипов", e);
                if (!cancelled) {
                    setCount(0);
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        fetchCount();
        return () => { cancelled = true };
    }, [workerpostId]);

    if (loading) return "Загрузка...";
    return count ?? 0;
}
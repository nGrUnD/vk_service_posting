import React, { useEffect, useState } from "react";
import api from "../api/axios";

export default function LastPostedDate({ workerpostId }) {
    const [date, setDate] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        const fetchDate = async () => {
            try {
                const res = await api.get(
                    `/users/{user_id}/workerpost/${workerpostId}/posted_clips/last_date`
                );
                if (!cancelled) {
                    setDate(res.data.last_date);
                }
            } catch (e) {
                console.error("Ошибка при получении даты последнего клипа", e);
                if (!cancelled) {
                    setDate(null);
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        fetchDate();
        return () => {
            cancelled = true;
        };
    }, [workerpostId]);

    if (loading) return "Загрузка...";

    if (!date) return "Нет данных";

    // форматирование
    const d = new Date(date);
    const formatted = d.toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).replace(",", " -"); // "16.09.2025 - 12:45"

    return formatted;
}

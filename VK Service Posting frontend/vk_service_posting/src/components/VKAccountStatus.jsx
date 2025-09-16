import React, { useEffect, useState } from "react";
import api from "../api/axios";

export default function AccountStatus({ workerpostId }) {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;

        const fetchStatus = async () => {
            try {
                const userId = localStorage.getItem("user_id");
                const res = await api.get(
                    `/users/{user_id}/workerpost/${workerpostId}/vk_account/block_status`
                );
                if (!cancelled) {
                    setStatus(res.data.status);
                }
            } catch (e) {
                console.error("Ошибка при получении статуса аккаунта", e);
                if (!cancelled) setStatus("Ошибка");
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        fetchStatus();
        return () => {
            cancelled = true;
        };
    }, [workerpostId]);

    if (loading) return "Загрузка...";

    if (status === "OK") return <span style={{ color: "green" }}>Активен</span>;
    if (status === "blocked") return <span style={{ color: "red" }}>Заблокирован</span>;

    return status || "Нет данных";
}
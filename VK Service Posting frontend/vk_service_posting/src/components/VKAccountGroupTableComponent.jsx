import React, { useEffect, useState, useCallback, useMemo } from "react";
import { Table, Spin, message, Input, Space } from "antd";
import api from "../api/axios";

export default function VkAccountGroupTable() {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);

    // состояние пагинации
    const [current, setCurrent] = useState(1);
    const [pageSize, setPageSize] = useState(100);
    const [total, setTotal] = useState(0);

    // фильтры по URL (клиентские)
    const [groupUrlFilter, setGroupUrlFilter] = useState("");
    const [accountUrlFilter, setAccountUrlFilter] = useState("");

    const fetchRows = useCallback(
        async (page = 1, size = 100) => {
            setLoading(true);
            const controller = new AbortController();
            try {
                const limit = size;
                const offset = (page - 1) * size;

                // Бэк возвращает { items: [...], count: number }
                const { data } = await api.get(`/users/{user_id}/vk_account_group/all`, {
                    params: { limit, offset },
                    signal: controller.signal,
                });

                setRows(Array.isArray(data?.items) ? data.items : []);
                setTotal(Number.isFinite(data?.count) ? data.count : 0);

                setCurrent(page);
                setPageSize(size);
            } catch (err) {
                if (err.name !== "CanceledError" && err.code !== "ERR_CANCELED") {
                    console.error("Ошибка при загрузке привязок VK", err);
                    message.error("Не удалось загрузить список привязок");
                }
            } finally {
                setLoading(false);
            }
            return () => controller.abort();
        },
        []
    );

    useEffect(() => {
        fetchRows(1, pageSize);
    }, [fetchRows, pageSize]);

    const handleTableChange = useCallback(
        (pagination) => {
            const { current: nextPage, pageSize: nextSize } = pagination;
            if (nextSize !== pageSize) {
                fetchRows(1, nextSize);
            } else {
                fetchRows(nextPage, nextSize);
            }
        },
        [fetchRows, pageSize]
    );

    // Клиентская фильтрация по URL
    const filteredRows = useMemo(() => {
        const g = groupUrlFilter.trim().toLowerCase();
        const a = accountUrlFilter.trim().toLowerCase();
        if (!g && !a) return rows;
        return rows.filter((r) => {
            const gUrl = r?.group?.vk_group_url?.toLowerCase() ?? "";
            const aUrl = r?.account?.vk_account_url?.toLowerCase() ?? "";
            const okG = g ? gUrl.includes(g) : true;
            const okA = a ? aUrl.includes(a) : true;
            return okG && okA;
        });
    }, [rows, groupUrlFilter, accountUrlFilter]);

    const columns = [
        { title: "ID (link)", dataIndex: "id", key: "id" }, // vk_account_group.id
        {
            title: "VK Group ID",
            key: "vk_group_id",
            render: (_, record) => record?.group?.vk_group_id ?? "—",
        },
        {
            title: "VK Account ID",
            key: "vk_account_id",
            render: (_, record) => record?.account?.vk_account_id ?? "—",
        },
        {
            title: "VK Group URL",
            key: "vk_group_url",
            render: (_, record) =>
                record?.group?.vk_group_url ? (
                    <a
                        href={record.group.vk_group_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline"
                    >
                        {record.group.vk_group_url}
                    </a>
                ) : (
                    "—"
                ),
        },
        {
            title: "VK Account URL",
            key: "vk_account_url",
            render: (_, record) =>
                record?.account?.vk_account_url ? (
                    <a
                        href={record.account.vk_account_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline"
                    >
                        {record.account.vk_account_url}
                    </a>
                ) : (
                    "—"
                ),
        },
        {
            title: "ФИО",
            key: "fio",
            render: (_, record) => {
                const name = record?.account?.name ?? "";
                const second = record?.account?.second_name ?? "";
                const full = [second, name].filter(Boolean).join(" ");
                return full || "—";
            },
        },
        {
            title: "Login",
            key: "login",
            render: (_, r) => r?.account?.login ?? "—",
        },
        { title: "Role", dataIndex: "role", key: "role" },
    ];

    return (
        <div className="mt-8">
            <h2 className="text-lg font-semibold mb-4">VK Аккаунты ↔ Паблики</h2>

            <Space style={{ marginBottom: 12 }}>
                <Input
                    allowClear
                    placeholder="Фильтр по VK Group URL"
                    value={groupUrlFilter}
                    onChange={(e) => setGroupUrlFilter(e.target.value)}
                    style={{ width: 280 }}
                />
                <Input
                    allowClear
                    placeholder="Фильтр по VK Account URL"
                    value={accountUrlFilter}
                    onChange={(e) => setAccountUrlFilter(e.target.value)}
                    style={{ width: 280 }}
                />
            </Space>

            <Spin spinning={loading}>
                <Table
                    rowKey="id"
                    columns={columns}
                    dataSource={filteredRows}
                    bordered
                    className="shadow-md"
                    pagination={{
                        current,
                        pageSize,
                        total, // теперь это реальный count с бэка
                        showSizeChanger: true,
                        pageSizeOptions: [20, 50, 100, 200],
                    }}
                    onChange={handleTableChange}
                />
            </Spin>
        </div>
    );
}
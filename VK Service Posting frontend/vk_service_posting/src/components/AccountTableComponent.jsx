import React, { useEffect, useState } from "react";
import { Table, Tag, Spin, Button, Popconfirm, message, Tooltip, Modal } from "antd";
import { CopyOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import api from "../api/axios";
import {
    PARSE_STATUS_TABLE_FILTERS,
    copyTextToClipboard,
    getAccountCurl,
    matchesParseStatusFilter,
} from "../utils/accountTableHelpers";

export default function AccountTable() {
    const [messageApi, contextHolder] = message.useMessage();
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [checkingCurlId, setCheckingCurlId] = useState(null);
    const [reconnectingCurlId, setReconnectingCurlId] = useState(null);
    const [collectingCurlId, setCollectingCurlId] = useState(null);
    const [infoAccount, setInfoAccount] = useState(null);

    const statusColors = {
        success: "green",
        failure: "red",
        pending: "orange",
        in_progress: "orange",
    };

    const fetchAccounts = async (silent = false) => {
        if (!silent) {
            setLoading(true);
        }
        try {
            const { data } = await api.get("/users/{user_id}/vk_accounts/all");
            // 👇 сортируем по id DESC перед рендером
            //const sortedData = [...data].sort((a, b) => b.id - a.id);
            //setAccounts(sortedData);
            setAccounts(data);
        } catch (err) {
            console.error("Ошибка при загрузке аккаунтов", err);
            messageApi.error("Не удалось загрузить аккаунты");
        } finally {
            if (!silent) {
                setLoading(false);
            }
        }
    };

    useEffect(() => {
        fetchAccounts();

        const intervalId = setInterval(() => {
            fetchAccounts(true);
        }, 10000);

        const handleVisibilityChange = () => {
            if (document.visibilityState === "visible") {
                fetchAccounts(true);
            }
        };
        document.addEventListener("visibilitychange", handleVisibilityChange);

        return () => {
            clearInterval(intervalId);
            document.removeEventListener("visibilitychange", handleVisibilityChange);
        };
    }, []);

    // Удаление аккаунта
    const handleDelete = async (id) => {
        try {
            await api.delete(`/users/{user_id}/vk_accounts/${id}`);
            messageApi.success("Аккаунт удален");
            fetchAccounts(); // обновить таблицу
        } catch (err) {
            console.error(err);
            messageApi.error("Ошибка при удалении аккаунта");
        }
    };

    const handleCheckCurl = async (id) => {
        setCheckingCurlId(id);
        try {
            const { data } = await api.post(`/users/{user_id}/vk_accounts/${id}/check_curl`);
            if (data?.ok) {
                messageApi.success(data?.detail || "curl живой");
            } else {
                messageApi.error(data?.detail || "Не удалось получить токен");
            }
            fetchAccounts(true);
        } catch (err) {
            console.error(err);
            messageApi.error(err?.response?.data?.detail || "Не удалось получить токен");
        } finally {
            setCheckingCurlId(null);
        }
    };

    const handleReconnectCurl = async (id) => {
        setReconnectingCurlId(id);
        try {
            await api.post(`/users/{user_id}/vk_accounts/${id}/reconnect_curl`);
            messageApi.success("Переподключение curl запущено");
            fetchAccounts(true);
        } catch (err) {
            console.error(err);
            messageApi.error(err?.response?.data?.detail || "Не удалось запустить переподключение curl");
        } finally {
            setReconnectingCurlId(null);
        }
    };

    const handleCollectCurl = async (id) => {
        setCollectingCurlId(id);
        try {
            const { data } = await api.post(`/users/{user_id}/vk_accounts/${id}/collect_curl`);
            if (data?.task_id) {
                messageApi.success("Сбор cURL запущен");
            } else {
                messageApi.info(data?.detail || "cURL уже сохранен");
            }
            fetchAccounts(true);
        } catch (err) {
            console.error(err);
            messageApi.error(err?.response?.data?.detail || "Не удалось запустить сбор cURL");
        } finally {
            setCollectingCurlId(null);
        }
    };

    const columns = [
        {
            title: "ID",
            dataIndex: "id",
            key: "id",
            sorter: (a, b) => a.id - b.id,
            defaultSortOrder: "descend",
            width: 90,
        },
        { title: "ID VK", dataIndex: "vk_account_id", key: "vk_account_id" },
        {
            title: "VK Аккаунт",
            key: "vk_account_url",
            render: (_, record) => (
                <a
                    href={record.vk_account_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline text-blue-500 flex items-center gap-2"
                >
                    <img
                        src={record.avatar_url}
                        alt={record.name}
                        className="w-6 h-6 rounded-full"
                    />
                    {`${record.name ?? ""} ${record.second_name ?? ""}`}
                </a>
            ),
        },
        {
            title: "Login",
            key: "login",
            render: (_, record) => {
                const login = record.login ?? "";
                const password = record.password ?? "";
                if (!login && !password) return "—";
                return `${login}:${password}`;
            },
        },
        {
            title: "ID Proxy",
            dataIndex: "proxy_id",
            key: "proxy_id",
            render: (val) => val ?? "-",
        },
        { title: "VK Паблики", dataIndex: "groups_count", key: "groups_count" },
        {
            title: "Флудконтроль",
            key: "floodControl",
            render: (_, record) => {
                if (record.flood_control && record.flood_control_time) {
                    return dayjs(record.flood_control_time).format("YYYY-MM-DD HH:mm");
                }
                return "Нет";
            },
        },
        {
            title: "Парсинг",
            dataIndex: "parse_status",
            key: "parse_status",
            filters: PARSE_STATUS_TABLE_FILTERS,
            onFilter: (value, record) => matchesParseStatusFilter(value, record.parse_status),
            render: (status) =>
                status ? (
                    <Tag color={statusColors[status] || "default"}>
                        {status.toUpperCase()}
                    </Tag>
                ) : (
                    "-"
                ),
        },
        {
            title: "Тип",
            dataIndex: "account_type",
            key: "account_type",
            filters: [
                { text: "main", value: "main" },
                { text: "connect", value: "connect" },
                { text: "backup", value: "backup" },
                { text: "posting", value: "posting" },
                { text: "blocked", value: "blocked" },
                { text: "checker", value: "checker" },
            ],
            onFilter: (value, record) => record.account_type === value,
        },
        {
            title: "Куки",
            dataIndex: "cookies",
            key: "cookies",
            render: (cookies) => (cookies ? "Есть" : "—"),
        },
        {
            title: "Действия",
            key: "actions",
            render: (_, record) => {
                const accountCurl = getAccountCurl(record);
                return (
                <div className="flex flex-wrap gap-2">
                    {accountCurl ? (
                        <Tooltip title="Копировать cURL">
                            <Button
                                size="small"
                                icon={<CopyOutlined />}
                                onClick={() =>
                                    copyTextToClipboard(accountCurl, messageApi, {
                                        success: "cURL скопирован в буфер",
                                    })
                                }
                            >
                                Скопировать курл
                            </Button>
                        </Tooltip>
                    ) : record.parse_status === "success" ? (
                        <Tooltip title="Собрать cURL для аккаунта">
                            <Button
                                size="small"
                                loading={collectingCurlId === record.id}
                                onClick={() => handleCollectCurl(record.id)}
                            >
                                Собрать курл
                            </Button>
                        </Tooltip>
                    ) : null}
                    <Button
                        size="small"
                        loading={checkingCurlId === record.id}
                        onClick={() => handleCheckCurl(record.id)}
                    >
                        Проверить curl
                    </Button>
                    <Popconfirm
                        title="Переподключить curl для этого аккаунта?"
                        okText="Да"
                        cancelText="Нет"
                        onConfirm={() => handleReconnectCurl(record.id)}
                    >
                        <Button
                            size="small"
                            loading={reconnectingCurlId === record.id}
                        >
                            Переподключить curl
                        </Button>
                    </Popconfirm>
                    <Popconfirm
                        title="Удалить аккаунт?"
                        okText="Да"
                        cancelText="Нет"
                        onConfirm={() => handleDelete(record.id)}
                    >
                        <Button danger size="small">
                            Удалить
                        </Button>
                    </Popconfirm>
                    <Button size="small" onClick={() => setInfoAccount(record)}>
                        Инфо
                    </Button>
                </div>
                );
            },
        },
    ];

    return (
        <div className="mt-8">
            {contextHolder}
            <h2 className="text-lg font-semibold mb-4">Подключённые аккаунты</h2>
            <Spin spinning={loading}>
                <Table
                    rowKey="id"
                    columns={columns}
                    dataSource={accounts}
                    bordered
                    className="shadow-md"
                    pagination={{
                        defaultPageSize: 10,
                        showSizeChanger: true,
                        pageSizeOptions: ["10", "20", "50", "100"],
                    }}
                />
            </Spin>
            <Modal
                open={Boolean(infoAccount)}
                title="Информация об аккаунте"
                onCancel={() => setInfoAccount(null)}
                footer={null}
                width={860}
            >
                <div className="space-y-4">
                    <div>
                        <div className="mb-1 text-xs font-semibold text-gray-500">cURL</div>
                        <div className="rounded border bg-gray-50 p-2">
                            <pre className="max-h-40 overflow-auto whitespace-pre-wrap break-all text-xs">
                                {getAccountCurl(infoAccount) || "—"}
                            </pre>
                        </div>
                        <div className="mt-2">
                            <Button
                                size="small"
                                onClick={() =>
                                    copyTextToClipboard(getAccountCurl(infoAccount), messageApi, {
                                        empty: "cURL отсутствует",
                                        success: "cURL скопирован",
                                    })
                                }
                            >
                                Копировать cURL
                            </Button>
                        </div>
                    </div>
                    <div>
                        <div className="mb-1 text-xs font-semibold text-gray-500">Cookie</div>
                        <div className="rounded border bg-gray-50 p-2">
                            <pre className="max-h-32 overflow-auto whitespace-pre-wrap break-all text-xs">
                                {infoAccount?.cookies || "—"}
                            </pre>
                        </div>
                        <div className="mt-2">
                            <Button
                                size="small"
                                onClick={() =>
                                    copyTextToClipboard(infoAccount?.cookies, messageApi, {
                                        empty: "Cookie отсутствует",
                                        success: "Cookie скопирован",
                                    })
                                }
                            >
                                Копировать cookie
                            </Button>
                        </div>
                    </div>
                    <div>
                        <div className="mb-1 text-xs font-semibold text-gray-500">Access token</div>
                        <div className="rounded border bg-gray-50 p-2">
                            <pre className="max-h-24 overflow-auto whitespace-pre-wrap break-all text-xs">
                                {infoAccount?.token || "—"}
                            </pre>
                        </div>
                        <div className="mt-2">
                            <Button
                                size="small"
                                onClick={() =>
                                    copyTextToClipboard(infoAccount?.token, messageApi, {
                                        empty: "Access token отсутствует",
                                        success: "Access token скопирован",
                                    })
                                }
                            >
                                Копировать access token
                            </Button>
                        </div>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
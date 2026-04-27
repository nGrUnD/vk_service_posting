import React, { useEffect, useMemo, useState } from "react";
import {
    Table,
    Tag,
    Spin,
    Button,
    Popconfirm,
    message,
    Tooltip,
    Segmented,
    Collapse,
    Dropdown,
    Typography,
} from "antd";
import { CopyOutlined, DownOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import api from "../api/axios";

const { Text: TypographyText } = Typography;
const BULK_PANEL_STORAGE_KEY = "accountCheckerBulkOpen";

export default function AccountTableChecker({ viewMode = "user", onViewModeChange }) {
    const [messageApi, contextHolder] = message.useMessage();
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [checkingCurlId, setCheckingCurlId] = useState(null);
    const [reconnectingCurlId, setReconnectingCurlId] = useState(null);
    const [changingPasswordId, setChangingPasswordId] = useState(null);
    const [selectedRowKeys, setSelectedRowKeys] = useState([]);
    const [bulkActionLoading, setBulkActionLoading] = useState(null);
    const [localMode, setLocalMode] = useState(viewMode);
    const [bulkOpenKeys, setBulkOpenKeys] = useState(() => {
        try {
            return sessionStorage.getItem(BULK_PANEL_STORAGE_KEY) === "1" ? ["bulk"] : [];
        } catch {
            return [];
        }
    });

    const activeViewMode = onViewModeChange ? viewMode : localMode;

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
            const { data } = await api.get("/users/{user_id}/vk_accounts/all_checker_connect");
            // 👇 сортируем по id DESC перед рендером
            const sortedData = [...data].sort((a, b) => b.id - a.id);
            setAccounts(sortedData);
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

    useEffect(() => {
        if (!onViewModeChange) {
            setLocalMode(viewMode);
        }
    }, [onViewModeChange, viewMode]);

    // Удаление аккаунта
    const deleteAccountRequest = async (id) => {
        await api.delete(`/users/{user_id}/vk_accounts/${id}`);
    };

    const handleDelete = async (id) => {
        try {
            await deleteAccountRequest(id);
            messageApi.success("Аккаунт удален.");
            fetchAccounts(); // обновить таблицу
        } catch (err) {
            console.error(err);
            messageApi.error(err?.response?.data?.detail || "Ошибка при удалении аккаунта");
        }
    };

    const checkCurlRequest = async (id) => {
        const { data } = await api.post(`/users/{user_id}/vk_accounts/${id}/check_curl`);
        if (!data?.ok) {
            throw new Error(data?.detail || "Не удалось проверить curl");
        }
        return data?.detail || "curl живой";
    };

    const handleCheckCurl = async (id) => {
        setCheckingCurlId(id);
        try {
            const detail = await checkCurlRequest(id);
            messageApi.success(detail);
            fetchAccounts(true);
        } catch (err) {
            console.error(err);
            messageApi.error(err?.response?.data?.detail || "Не удалось получить токен");
        } finally {
            setCheckingCurlId(null);
        }
    };

    const reconnectCurlRequest = async (id) => {
        await api.post(`/users/{user_id}/vk_accounts/${id}/reconnect_curl`);
    };

    const handleReconnectCurl = async (id) => {
        setReconnectingCurlId(id);
        try {
            await reconnectCurlRequest(id);
            messageApi.success("Переподключение curl запущено.");
            fetchAccounts(true);
        } catch (err) {
            console.error(err);
            messageApi.error(err?.response?.data?.detail || "Не удалось запустить переподключение curl");
        } finally {
            setReconnectingCurlId(null);
        }
    };

    const getRecordLoginPass = (record) => {
        const login = record?.login ?? "";
        const password = record?.password ?? "";
        if (!login || !password) {
            return null;
        }
        return `${login}:${password}`;
    };

    const copyLoginPassToClipboard = async (text) => {
        if (!text) {
            return;
        }
        try {
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(text);
                messageApi.success("Скопировано в буфер");
            } else {
                messageApi.warning("Буфер обмена недоступен");
            }
        } catch (e) {
            console.error(e);
            messageApi.error("Не удалось скопировать");
        }
    };

    const handleChangePassword = async (record) => {
        const loginPass = getRecordLoginPass(record);
        if (!loginPass) {
            messageApi.warning("Для смены пароля у аккаунта должен быть login:password.");
            return;
        }

        setChangingPasswordId(record.id);
        try {
            const payload = { accounts: [loginPass] };
            const { data } = await api.post("/tools/{user_id}/account_change_passwords", payload);
            const updated = data?.new_accounts?.[0];
            if (!updated) {
                messageApi.warning("Пароль не был изменён.");
                return;
            }

            const result = `${updated.login}:${updated.password}`;
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(result);
            }
            messageApi.success("Пароль изменён. Новый login:pass скопирован в буфер.");
            fetchAccounts(true);
        } catch (err) {
            console.error(err);
            messageApi.error(err?.response?.data?.detail || "Ошибка при смене пароля");
        } finally {
            setChangingPasswordId(null);
        }
    };

    const selectedAccounts = useMemo(
        () => accounts.filter((item) => selectedRowKeys.includes(item.id)),
        [accounts, selectedRowKeys]
    );

    const runBulkAction = async (actionKey, actionFn, successText) => {
        if (!selectedRowKeys.length) {
            messageApi.warning("Сначала выделите аккаунты.");
            return;
        }
        setBulkActionLoading(actionKey);

        let successCount = 0;
        let failCount = 0;

        for (const id of selectedRowKeys) {
            try {
                await actionFn(id);
                successCount += 1;
            } catch (err) {
                console.error(err);
                failCount += 1;
            }
        }

        if (successCount > 0) {
            messageApi.success(`${successText}: ${successCount}`);
        }
        if (failCount > 0) {
            messageApi.warning(`С ошибкой: ${failCount}`);
        }

        setBulkActionLoading(null);
        fetchAccounts(true);
    };

    const handleBulkChangePasswords = async () => {
        if (!selectedAccounts.length) {
            messageApi.warning("Сначала выделите аккаунты.");
            return;
        }

        const credentials = selectedAccounts
            .map(getRecordLoginPass)
            .filter(Boolean);

        if (!credentials.length) {
            messageApi.warning("У выделенных аккаунтов нет login:password.");
            return;
        }

        setBulkActionLoading("change-password");
        try {
            const { data } = await api.post("/tools/{user_id}/account_change_passwords", {
                accounts: credentials,
            });
            const newLogins = (data?.new_accounts || [])
                .map((item) => `${item.login}:${item.password}`)
                .join("\n");
            if (newLogins && navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(newLogins);
            }
            messageApi.success("Пароли изменены. Новые login:pass скопированы в буфер.");
            fetchAccounts(true);
        } catch (err) {
            console.error(err);
            messageApi.error(err?.response?.data?.detail || "Ошибка при смене паролей");
        } finally {
            setBulkActionLoading(null);
        }
    };

    const renderStatusCell = (record) => {
        const publishUrl = record?.posting_public_url || record?.posting_url || record?.public_url;
        if (publishUrl) {
            return (
                <a
                    href={publishUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                >
                    ПОСТИТ
                </a>
            );
        }

        if (record?.posting_status === "posting") {
            return <Tag color="blue">ПОСТИТ</Tag>;
        }

        const status = record?.parse_status;
        if (status) {
            return <Tag color={statusColors[status] || "default"}>{status.toUpperCase()}</Tag>;
        }

        return "-";
    };

    const renderDeveloperRowActions = (record) => (
        <Dropdown
            trigger={["click"]}
            dropdownRender={() => (
                <div
                    className="min-w-[220px] rounded border border-gray-200 bg-white p-2 shadow-md"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="flex flex-col gap-1">
                        <Tooltip title="Проверяет, что у аккаунта рабочий curl/токен" placement="left">
                            <Button
                                size="small"
                                block
                                loading={checkingCurlId === record.id}
                                onClick={() => handleCheckCurl(record.id)}
                            >
                                Проверить curl
                            </Button>
                        </Tooltip>
                        <Popconfirm
                            title="Переподключить curl для этого аккаунта?"
                            okText="Да"
                            cancelText="Нет"
                            onConfirm={() => handleReconnectCurl(record.id)}
                        >
                            <Button
                                size="small"
                                block
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
                            <Button danger size="small" block>
                                Удалить
                            </Button>
                        </Popconfirm>
                        <Tooltip title="Меняет пароль и копирует новый login:pass в буфер" placement="left">
                            <Button
                                size="small"
                                block
                                loading={changingPasswordId === record.id}
                                onClick={() => handleChangePassword(record)}
                            >
                                Сменить пароль
                            </Button>
                        </Tooltip>
                    </div>
                </div>
            )}
        >
            <Button size="small" className="!px-2">
                Действия <DownOutlined />
            </Button>
        </Dropdown>
    );

    const userColumns = [
        {
            title: "Log:pass",
            key: "login_pass",
            width: 220,
            render: (_, record) => {
                const loginPass = getRecordLoginPass(record);
                if (!loginPass) {
                    return <span className="text-gray-400">—</span>;
                }
                return (
                    <div className="flex min-w-0 items-center gap-0.5">
                        <span className="min-w-0 flex-1 truncate font-mono text-xs select-text">
                            {loginPass}
                        </span>
                        <Tooltip title="Копировать login:pass">
                            <Button
                                type="text"
                                size="small"
                                className="!shrink-0 !px-1 text-gray-500 hover:text-blue-600"
                                icon={<CopyOutlined />}
                                onClick={() => copyLoginPassToClipboard(loginPass)}
                                aria-label="Копировать login:pass"
                            />
                        </Tooltip>
                    </div>
                );
            },
        },
        {
            title: "Пачка",
            key: "checker_batch",
            width: 130,
            ellipsis: true,
            render: (_, record) => {
                const name = record.checker_batch_label;
                if (!name) {
                    return <span className="text-gray-400">—</span>;
                }
                return (
                    <Tooltip title={name}>
                        <Tag color="geekblue" className="!m-0 !max-w-full truncate">
                            {name}
                        </Tag>
                    </Tooltip>
                );
            },
        },
        {
            title: "Статус",
            key: "status",
            width: 160,
            render: (_, record) => renderStatusCell(record),
        },
        {
            title: "Действия",
            key: "actions",
            render: (_, record) => (
                <div className="flex flex-wrap gap-2">
                    <Tooltip title="Проверяет, что у аккаунта рабочий curl/токен">
                        <Button
                            size="small"
                            loading={checkingCurlId === record.id}
                            onClick={() => handleCheckCurl(record.id)}
                        >
                            Проверить curl
                        </Button>
                    </Tooltip>
                    <Tooltip title="Запускает переподключение curl через login:password">
                        <Popconfirm
                            title="Переподключить curl для этого аккаунта?"
                            okText="Да"
                            cancelText="Нет"
                            onConfirm={() => handleReconnectCurl(record.id)}
                        >
                            <Button size="small" loading={reconnectingCurlId === record.id}>
                                Переподключить curl
                            </Button>
                        </Popconfirm>
                    </Tooltip>
                    <Tooltip title="Удаляет аккаунт из текущей таблицы">
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
                    </Tooltip>
                    <Tooltip title="Меняет пароль и копирует новый login:pass в буфер">
                        <Button
                            size="small"
                            loading={changingPasswordId === record.id}
                            onClick={() => handleChangePassword(record)}
                        >
                            Сменить пароль
                        </Button>
                    </Tooltip>
                </div>
            ),
        },
    ];

    const developerColumns = [
        {
            title: "ID",
            dataIndex: "id",
            key: "id",
            sorter: (a, b) => a.id - b.id,
            defaultSortOrder: "descend",
            width: 64,
        },
        { title: "ID VK", dataIndex: "vk_account_id", key: "vk_account_id", ellipsis: true },
        {
            title: "VK Аккаунт",
            key: "vk_account_url",
            ellipsis: { showTitle: false },
            render: (_, record) => {
                const text = `${record.name ?? ""} ${record.second_name ?? ""}`.trim() || "—";
                return (
                    <a
                        href={record.vk_account_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline text-blue-500 flex min-w-0 items-start gap-1.5"
                    >
                        <img
                            src={record.avatar_url}
                            alt=""
                            className="h-5 w-5 shrink-0 rounded-full"
                        />
                        <TypographyText ellipsis={{ tooltip: true }} className="!mb-0 min-w-0 !max-w-full text-inherit">
                            {text}
                        </TypographyText>
                    </a>
                );
            },
        },
        {
            title: "Login",
            key: "login",
            ellipsis: { showTitle: false },
            render: (_, record) => {
                const login = record.login ?? "";
                const password = record.password ?? "";
                if (!login && !password) return "—";
                const line = `${login}:${password}`;
                return (
                    <div className="flex min-w-0 items-center gap-0.5">
                        <TypographyText
                            ellipsis={{ tooltip: true }}
                            className="!mb-0 min-w-0 flex-1 font-mono text-xs"
                        >
                            {line}
                        </TypographyText>
                        <Tooltip title="Копировать login:pass">
                            <Button
                                type="text"
                                size="small"
                                className="!shrink-0 !px-1 text-gray-500 hover:text-blue-600"
                                icon={<CopyOutlined />}
                                onClick={() => copyLoginPassToClipboard(line)}
                                aria-label="Копировать login:pass"
                            />
                        </Tooltip>
                    </div>
                );
            },
        },
        {
            title: "Пачка",
            key: "checker_batch",
            width: 100,
            ellipsis: true,
            render: (_, record) => {
                const name = record.checker_batch_label;
                if (!name) {
                    return <span className="text-gray-400">—</span>;
                }
                return (
                    <Tooltip title={name}>
                        <Tag color="geekblue" className="!m-0 !max-w-full truncate text-xs">
                            {name}
                        </Tag>
                    </Tooltip>
                );
            },
        },
        {
            title: "ID Proxy",
            dataIndex: "proxy_id",
            key: "proxy_id",
            ellipsis: true,
            render: (val) => val ?? "-",
        },
        { title: "Паблики", dataIndex: "groups_count", key: "groups_count", align: "right" },
        {
            title: "Флуд",
            key: "floodControl",
            ellipsis: true,
            render: (_, record) => {
                if (record.flood_control && record.flood_control_time) {
                    return dayjs(record.flood_control_time).format("DD.MM.YY HH:mm");
                }
                return "Нет";
            },
        },
        {
            title: "Парсинг",
            dataIndex: "parse_status",
            key: "parse_status",
            render: (_, record) => renderStatusCell(record),
        },
        {
            title: "Тип",
            dataIndex: "account_type",
            key: "account_type",
            filters: [
                { text: "connect", value: "connect" },
                { text: "checker", value: "checker" },
            ],
            onFilter: (value, record) => record.account_type === value,
        },
        {
            title: "Куки",
            dataIndex: "cookies",
            key: "cookies",
            render: (cookies) => (cookies ? "Да" : "—"),
        },
        {
            title: "Действия",
            key: "actions",
            width: 102,
            align: "center",
            render: (_, record) => renderDeveloperRowActions(record),
        },
    ];

    const handleBulkPanelChange = (keys) => {
        const next = Array.isArray(keys) ? keys : keys != null ? [keys] : [];
        setBulkOpenKeys(next);
        try {
            sessionStorage.setItem(BULK_PANEL_STORAGE_KEY, next.includes("bulk") ? "1" : "0");
        } catch {
            /* ignore */
        }
    };

    const bulkPanelLabel = (
        <span className="font-medium">
            Операции с выделенными
            {selectedRowKeys.length > 0 ? (
                <span className="ml-2 text-gray-500">({selectedRowKeys.length} выд.)</span>
            ) : null}
        </span>
    );

    const checkerBatchRowClassName = (record) => {
        if (record?.account_checker_batch_id == null) {
            return "";
        }
        const idx = Math.abs(Number(record.account_checker_batch_id)) % 4;
        return `checker-batch-row-${idx}`;
    };

    return (
        <div className="mt-8">
            {contextHolder}
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold">Подключённые аккаунты</h2>
                <Segmented
                    options={[
                        { label: "Пользователь", value: "user" },
                        { label: "Разработчик", value: "developer" },
                    ]}
                    value={activeViewMode}
                    onChange={(nextMode) => {
                        if (onViewModeChange) {
                            onViewModeChange(nextMode);
                        } else {
                            setLocalMode(nextMode);
                        }
                    }}
                />
            </div>

            <div className="w-full min-w-0">
                <Collapse
                    size="small"
                    bordered
                    className="mb-3 bg-white"
                    activeKey={bulkOpenKeys}
                    onChange={handleBulkPanelChange}
                    items={[
                        {
                            key: "bulk",
                            label: bulkPanelLabel,
                            children: (
                                <div className="flex flex-wrap gap-2">
                                    <TypographyText type="secondary" className="!mb-0 block w-full text-sm">
                                        Выбрано аккаунтов: <strong>{selectedRowKeys.length}</strong>
                                    </TypographyText>
                                    <Tooltip title="Проверка curl/токена для всех выделенных аккаунтов">
                                        <Button
                                            size="small"
                                            loading={bulkActionLoading === "check"}
                                            onClick={() => runBulkAction("check", checkCurlRequest, "Проверено")}
                                        >
                                            Проверить curl
                                        </Button>
                                    </Tooltip>
                                    <Tooltip title="Массовое переподключение curl для выделенных аккаунтов">
                                        <Button
                                            size="small"
                                            loading={bulkActionLoading === "reconnect"}
                                            onClick={() =>
                                                runBulkAction("reconnect", reconnectCurlRequest, "Переподключено")
                                            }
                                        >
                                            Переподключить curl
                                        </Button>
                                    </Tooltip>
                                    <Tooltip title="Массовая смена пароля по login:password">
                                        <Button
                                            size="small"
                                            loading={bulkActionLoading === "change-password"}
                                            onClick={handleBulkChangePasswords}
                                        >
                                            Сменить пароль
                                        </Button>
                                    </Tooltip>
                                    <Tooltip title="Массовое удаление выделенных аккаунтов">
                                        <Popconfirm
                                            title="Удалить выделенные аккаунты?"
                                            okText="Да"
                                            cancelText="Нет"
                                            onConfirm={() => runBulkAction("delete", deleteAccountRequest, "Удалено")}
                                        >
                                            <Button
                                                danger
                                                size="small"
                                                loading={bulkActionLoading === "delete"}
                                            >
                                                Удалить
                                            </Button>
                                        </Popconfirm>
                                    </Tooltip>
                                </div>
                            ),
                        },
                    ]}
                />

                <Spin spinning={loading}>
                    <Table
                        rowKey="id"
                        size="small"
                        tableLayout="fixed"
                        rowClassName={checkerBatchRowClassName}
                        rowSelection={{
                            selectedRowKeys,
                            onChange: setSelectedRowKeys,
                            columnWidth: 48,
                        }}
                        columns={activeViewMode === "developer" ? developerColumns : userColumns}
                        dataSource={accounts}
                        bordered
                        className={`shadow-md compact-account-table w-full ${
                            activeViewMode === "developer" ? "developer-mode-table" : ""
                        }`}
                        pagination={{
                            defaultPageSize: 10,
                            showSizeChanger: true,
                            pageSizeOptions: ["10", "20", "50", "100"],
                        }}
                    />
                </Spin>
            </div>
        </div>
    );
}
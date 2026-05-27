export const PARSE_STATUS_TABLE_FILTERS = [
    { text: "Success", value: "success" },
    { text: "Failed", value: "failure" },
    { text: "Pending", value: "pending" },
];

export function matchesParseStatusFilter(filterValue, parseStatus) {
    const status = (parseStatus || "").toLowerCase();
    if (filterValue === "pending") {
        return status === "pending" || status === "in_progress";
    }
    return status === filterValue;
}

export function getAccountCurl(record) {
    const curl = record?.curl;
    return typeof curl === "string" && curl.trim() ? curl.trim() : null;
}

export async function copyTextToClipboard(text, messageApi, messages = {}) {
    const {
        success = "Скопировано в буфер",
        empty = "Нечего копировать",
        error = "Не удалось скопировать",
    } = messages;

    if (!text) {
        messageApi.warning(empty);
        return;
    }
    try {
        if (navigator?.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
            messageApi.success(success);
        } else {
            messageApi.warning("Буфер обмена недоступен");
        }
    } catch (e) {
        console.error(e);
        messageApi.error(error);
    }
}

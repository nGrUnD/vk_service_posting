import React from 'react';

const CurlInputField = ({ value, onChange }) => (
    <div>
        <label
            htmlFor="curl-input"
            style={{ fontWeight: 600, marginBottom: 4, display: 'block' }}
        >
            Команда cURL
        </label>
        <textarea
            id="curl-input"
            placeholder="Вставьте сюда вашу команду cURL"
            rows={3}
            value={value}
            onChange={e => onChange(e.target.value)}
            style={{ width: '100%', padding: 8 }}
        />
    </div>
);

export default CurlInputField;

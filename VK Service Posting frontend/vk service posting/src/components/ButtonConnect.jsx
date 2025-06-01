import React from 'react';
import { Button } from 'antd';

const ButtonConnect = ({ loading, onClick }) => (
    <Button
        type="primary"
        loading={loading}
        onClick={onClick}
        block
    >
        Подключить
    </Button>
);

export default ButtonConnect;
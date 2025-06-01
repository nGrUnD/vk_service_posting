import React from 'react';
import { Avatar } from 'antd';

export default function AccountAvatar({ avatarUrl }) {
    return (
        <div className="flex flex-col items-center">
            <Avatar
                size={{ xs: 24, sm: 32, md: 40, lg: 64, xl: 80, xxl: 150 }}
                src={avatarUrl || 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Circle-icons-profile.svg/512px-Circle-icons-profile.svg.png'}
            />
        </div>
    )
}

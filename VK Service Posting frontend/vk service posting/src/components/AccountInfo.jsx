import React from 'react';

export default function AccountInfo({ name, groupsCount, vkAccountUrl }) {
    return (
        <div className="space-y-1">
            {vkAccountUrl ? (
                <a
                    href={vkAccountUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xl font-semibold text-blue-600 hover:underline"
                >
                    {name}
                </a>
            ) : (
                <h2 className="text-xl font-semibold">{name}</h2>
            )}
            <p className="text-gray-600">
                Групп: {groupsCount || 0}
            </p>
        </div>
    );
}

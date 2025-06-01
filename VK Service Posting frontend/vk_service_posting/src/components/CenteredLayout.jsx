// src/components/CenteredLayout.jsx
import React from 'react';
import { Outlet } from 'react-router-dom';

export default function CenteredLayout({ title }) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full p-8 shadow-lg bg-white">
                {title && (
                    <h2 className="text-2xl font-bold text-center mb-6">{title}</h2>
                )}
                <Outlet />
            </div>
        </div>
    );
}
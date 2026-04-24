import React from 'react';

export default function ComingSoonPage({ title, description }) {
  return (
    <section className="v2-card rounded-[28px] p-8">
      <div className="max-w-2xl">
        <div className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-400">
          V2 workspace
        </div>
        <h3 className="mt-3 text-3xl font-semibold text-white">{title}</h3>
        <p className="v2-muted mt-4 text-base">{description}</p>

        <div className="mt-8 rounded-[24px] border border-dashed border-indigo-400/30 bg-indigo-500/6 p-5 text-sm text-slate-300">
          Маршрут уже живет в отдельном frontend и не конфликтует с текущим `V1`. Сюда можно
          переносить готовый код нового макета по мере интеграции.
        </div>
      </div>
    </section>
  );
}

import { useEffect } from 'react';
import type { RegistroIndicador } from '../api';

export function IndicadorDetalhes({ titulo, registros, fechar }: { titulo: string; registros: RegistroIndicador[]; fechar: () => void }) {
  useEffect(() => {
    const old = document.activeElement as HTMLElement | null;
    const dialog = document.getElementById('indicador-dialog') as HTMLDialogElement;
    dialog.showModal();
    return () => { dialog.close(); old?.focus(); };
  }, []);
  return <dialog id="indicador-dialog" onCancel={fechar} className="m-auto w-[min(900px,94vw)] max-h-[85vh] rounded-xl bg-slate-900 text-white p-6 backdrop:bg-black/70" aria-labelledby="indicador-titulo">
    <div className="flex justify-between gap-4 mb-5"><h2 id="indicador-titulo" className="text-xl font-bold">{titulo} · {registros.length} registros</h2><button autoFocus onClick={fechar} className="rounded px-3 py-1 bg-slate-700">Fechar</button></div>
    <div className="overflow-auto max-h-[65vh]"><table className="w-full text-left text-sm"><thead><tr><th className="p-3">Colaborador</th><th className="p-3">Setor</th><th className="p-3">Data</th></tr></thead><tbody>{registros.map((r,i)=><tr key={r.id || i} className="border-t border-white/10"><td className="p-3">{r.nome}</td><td className="p-3">{r.setor}</td><td className="p-3">{r.data?.slice(0,10).split('-').reverse().join('/') || 'Não informada'}</td></tr>)}</tbody></table>{registros.length===0 && <p className="p-4 text-slate-300">Nenhum registro nesta competência e setor.</p>}</div>
  </dialog>;
}

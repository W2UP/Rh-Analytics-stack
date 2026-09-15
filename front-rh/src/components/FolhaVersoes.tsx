import { useEffect, useState } from 'react';
import { apiFetch } from '../api';

interface Versao { id: number; usuario: string; criado_em: string }
export function FolhaVersoes({ mes, ano, atualizacao }: { mes: number; ano: number; atualizacao: string }) {
  const [versoes,setVersoes] = useState<Versao[]>([]);
  const [erro,setErro] = useState('');
  useEffect(()=>{
    const controller = new AbortController();
    apiFetch(`/folha/versoes?mes=${mes}&ano=${ano}`,{signal:controller.signal}).then(r=>r.json()).then(v=>{setVersoes(v);setErro('');}).catch(e=>{if(e.name!=='AbortError')setErro(e.message);});
    return ()=>controller.abort();
  },[mes,ano,atualizacao]);
  const download = async (id:number) => {
    try {
      const r=await apiFetch(`/folha/versoes/${id}`); const data=await r.json();
      const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
      const a=document.createElement('a'); a.href=url;a.download=`folha-${ano}-${mes}-versao-${id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    } catch(e) {setErro((e as Error).message);}
  };
  return <details className="p-4 mb-4 rounded-xl bg-slate-800 text-slate-100"><summary className="cursor-pointer font-semibold">Histórico dos fechamentos ({versoes.length})</summary>{erro && <p role="alert">{erro}</p>}<ul className="mt-3 space-y-2">{versoes.map(v=><li key={v.id} className="flex flex-wrap justify-between gap-2"><span>Versão {v.id} · {v.usuario} · {new Date(v.criado_em).toLocaleString('pt-BR')}</span><button onClick={()=>download(v.id)} className="underline">Baixar registros</button></li>)}</ul>{!versoes.length && <p className="mt-2 text-sm">As versões serão preservadas ao salvar o próximo fechamento.</p>}</details>;
}

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiFetch } from '../api';
import type { RegistroIndicador, SyncStatus } from '../api';
const initial = {
    funcionarios: "-", admissoes: "-", desligamentos: "-", turnover: "-", 
    atestados: "-", advertencias: "-", faltas: "-", atrasos: "-", avaliacoes: "-",
    custo_absenteismo: 0, graficoSetores: [], graficoTurnover: [], graficoMotivos: [], graficoHeadcount: [],
    alertasAniversarios: [], alertasContratos: [], graficoAdvertencias: [], rankingFaltas: [], rankingAtestados: [], rankingAdvertencias: [],
    rankingMedicos: [], rankingCids: [], graficoRadar: [], perfis360: {} as Record<string, any>,
    alertasFerias: [], totalHorasExtras: 0, graficoHorasExtras: [], armarios: [], setoresDisponiveis: [],
    periodo_fiscal: "",
    detalhes: { funcionarios: [], admissoes: [], desligamentos: [] } as Record<string, RegistroIndicador[]>,
    avisos: [] as string[], comparacao: {} as Record<string,number>,
    base_turnover: { formula: '', quadro_fim: 0, desligamentos: 0 } 
  };

export function useDashboard(autenticado: boolean, mes: number, ano: number, setor: string) {
  const [kpis,setKpis] = useState(initial);
  const [carregandoDados,setCarregandoDados] = useState(false);
  const [erroDados,setErroDados] = useState('');
  const [syncStatus,setSyncStatus] = useState<SyncStatus | null>(null);
  const [sincronizando,setSincronizando] = useState(false);
  const [revision,setRevision] = useState(0);
  const previousStatus = useRef('');
  const carregarDadosDashboard = useCallback(()=>setRevision(r=>r+1),[]);
  useEffect(()=>{
    if(!autenticado) {setKpis(initial);setSyncStatus(null);return;}
    const controller=new AbortController();
    setCarregandoDados(true);setErroDados('');
    const query=new URLSearchParams({mes:String(mes),ano:String(ano),setor});
    apiFetch(`/dashboard/kpis?${query}`,{signal:controller.signal}).then(r=>r.json()).then(data=>{
      if(controller.signal.aborted)return;
      setKpis({...initial,...data});setSyncStatus(data.sincronizacao);
    }).catch(e=>{if(e.name!=='AbortError')setErroDados(e.message);}).finally(()=>{if(!controller.signal.aborted)setCarregandoDados(false);});
    return ()=>controller.abort();
  },[autenticado,mes,ano,setor,revision]);
  useEffect(()=>{
    if(!autenticado)return;
    let stopped=false; let timer: ReturnType<typeof setTimeout>;
    const controller=new AbortController();
    const poll=async()=>{
      try {
        const r=await apiFetch('/sincronizar/status',{signal:controller.signal});const status:SyncStatus=await r.json();
        if(stopped)return;
        setSyncStatus(status);setSincronizando(status.status==='running');
        if(previousStatus.current==='running' && status.status==='success')carregarDadosDashboard();
        previousStatus.current=status.status;
        timer=setTimeout(poll,status.status==='running'?1500:15000);
      } catch(e) {if(!stopped){setErroDados((e as Error).message);timer=setTimeout(poll,15000);}}
    };
    poll();return()=>{stopped=true;controller.abort();clearTimeout(timer);};
  },[autenticado,carregarDadosDashboard]);
  const forcarSincronizacao=async()=>{
    setSincronizando(true);setErroDados('');previousStatus.current='running';
    try {await apiFetch('/sincronizar',{method:'POST'});}
    catch(e){setSincronizando(false);setErroDados((e as Error).message);}
  };
  return {kpis,carregandoDados,sincronizando,erroDados,syncStatus,carregarDadosDashboard,forcarSincronizacao};
}

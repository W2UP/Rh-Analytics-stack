import { useState, useEffect } from 'react';
import { LayoutDashboard, Users, UserPlus, UserMinus, Activity, Stethoscope, AlertOctagon, Clock, Star, UsersRound, Download, TrendingDown, Lock, PieChart as PieChartIcon, DollarSign, Calendar, Gift, BellRing, AlertTriangle, Loader2 } from 'lucide-react';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';

const CORES_DONUT = ['#818CF8', '#F43F5E', '#34D399', '#FBBF24', '#A78BFA', '#F472B6'];
const CORES_ADVERTENCIA = ['#F59E0B', '#EF4444', '#EC4899', '#8B5CF6', '#3B82F6'];
const NOME_MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

export function App() {
  const [autenticado, setAutenticado] = useState(() => { return localStorage.getItem("rh_logado") === "true"; });
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erroLogin, setErroLogin] = useState("");
  const [fazendoLogin, setFazendoLogin] = useState(false);

  const [carregandoDados, setCarregandoDados] = useState(true);
  const [mesSelecionado, setMesSelecionado] = useState(new Date().getMonth() + 1); 
  const [anoSelecionado, setAnoSelecionado] = useState(new Date().getFullYear()); 

  const [filtroContrato, setFiltroContrato] = useState("45 Dias"); 
  const [filtroSemana, setFiltroSemana] = useState(0); 

  const [modoImpressao, setModoImpressao] = useState(false);

  const [kpis, setKpis] = useState({
    funcionarios: "-", admissoes: "-", desligamentos: "-", turnover: "-", 
    atestados: "-", advertencias: "-", faltas: "-", atrasos: "-", avaliacoes: "-",
    custo_absenteismo: 0,
    graficoSetores: [], graficoTurnover: [], graficoMotivos: [], graficoHeadcount: [],
    alertasAniversarios: [], alertasContratos: [],
    graficoAdvertencias: [], rankingFaltas: [], rankingAtestados: [],
    rankingMedicos: [], rankingCids: [],
    graficoRadar: [] 
  });

  const [menuAtivo, setMenuAtivo] = useState("visao_geral");
  const [gerandoPdf, setGerandoPdf] = useState(false);

  useEffect(() => { if (autenticado) { carregarDadosDashboard(); } }, [autenticado, mesSelecionado, anoSelecionado]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault(); setFazendoLogin(true); setErroLogin("");
    try {
      const resposta = await fetch("http://127.0.0.1:8000/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario, senha }) });
      const dados = await resposta.json();
      if (dados.sucesso) { localStorage.setItem("rh_logado", "true"); setAutenticado(true); } 
      else { setErroLogin("Usuário ou senha incorretos."); }
    } catch (erro) { setErroLogin("Servidor Offline. Verifique terminal Python."); } 
    finally { setFazendoLogin(false); }
  };

  const handleLogout = () => { localStorage.removeItem("rh_logado"); setAutenticado(false); };
  
  const carregarDadosDashboard = () => {
    setCarregandoDados(true); 
    fetch(`http://127.0.0.1:8000/api/dashboard/kpis?mes=${mesSelecionado}&ano=${anoSelecionado}`)
      .then((resposta) => resposta.json())
      .then((dados_reais) => {
        setKpis(dados_reais);
        setCarregandoDados(false); 
      })
      .catch((erro) => {
        console.error("Erro ao buscar dados:", erro);
        setCarregandoDados(false);
      });
  };
  
  const formatarMoeda = (valor: number | string) => {
    if (valor === "-" || isNaN(Number(valor))) return "R$ 0,00";
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor));
  };
  
  // ==========================================
  // FUNÇÃO BLINDADA DO PDF (MOLDE DE CONCRETO)
  // ==========================================
  const exportarPDF = async () => {
    if (kpis.funcionarios === "-") {
      alert("Aguarde os dados terminarem de sincronizar antes de gerar o relatório.");
      return;
    }

    try {
      setGerandoPdf(true); 
      setModoImpressao(true); 
      
      // Dá 2 segundos exatos para o navegador montar a tela de 1200px e desenhar os gráficos
      await new Promise((resolve) => setTimeout(resolve, 2000)); 

      const pdf = new jsPDF('l', 'mm', 'a4'); 
      const pdfWidth = pdf.internal.pageSize.getWidth();
      
      const paginas = ['print-visao', 'print-comportamento', 'print-desempenho'];
      let primeiraPagina = true;

      for (const pageId of paginas) {
        const element = document.getElementById(pageId);
        if (element) {
          const canvas = await html2canvas(element, { 
            scale: 2, 
            useCORS: true, 
            backgroundColor: "#F8FAFC" 
          });
          
          if (canvas.width === 0) continue; // Evita erro se o canvas bugar

          const imgData = canvas.toDataURL('image/png');
          
          // Calcula a altura proporcional
          const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

          if (!primeiraPagina) { pdf.addPage(); }
          
          // Desenha na folha A4 com uma pequena margem superior (5)
          pdf.addImage(imgData, 'PNG', 0, 5, pdfWidth, pdfHeight);
          primeiraPagina = false;
        }
      }
      
      pdf.save(`Relatorio_Executivo_RH_${NOME_MESES[mesSelecionado-1]}_${anoSelecionado}.pdf`);
    } catch (erro: any) { 
      console.error("Erro no Gerador:", erro);
      alert(`Ops, ocorreu um erro técnico ao gerar: ${erro.message}`); 
    } finally { 
      setModoImpressao(false); 
      setGerandoPdf(false); 
    }
  };
  
  const dataHoje = new Date();
  const mesAtualHoje = dataHoje.getMonth() + 1;
  const anoAtualHoje = dataHoje.getFullYear();
  const diaAtual = dataHoje.getDate();

  const verificarUrgencia = (diaVencimento: number) => {
    if (mesSelecionado !== mesAtualHoje || anoSelecionado !== anoAtualHoje) return null; 
    const diasRestantes = diaVencimento - diaAtual;
    if (diasRestantes === 0) return "VENCE HOJE!";
    if (diasRestantes > 0 && diasRestantes <= 7) return `Em ${diasRestantes} dias`;
    if (diasRestantes < 0) return `Venceu há ${Math.abs(diasRestantes)} dias`;
    return null;
  };

  const contratosFiltrados = kpis.alertasContratos?.filter((c: any) => c.tipo === filtroContrato).sort((a: any, b: any) => {
    const urgA = verificarUrgencia(a.dia); const urgB = verificarUrgencia(b.dia);
    if (urgA && !urgB) return -1; if (!urgA && urgB) return 1; return a.dia - b.dia;
  }) || [];
  
  const aniversariosFiltrados = kpis.alertasAniversarios?.filter((a: any) => {
    if (filtroSemana === 0) return true;
    if (filtroSemana === 1) return a.dia >= 1 && a.dia <= 7;
    if (filtroSemana === 2) return a.dia >= 8 && a.dia <= 14;
    if (filtroSemana === 3) return a.dia >= 15 && a.dia <= 21;
    if (filtroSemana === 4) return a.dia >= 22 && a.dia <= 28;
    if (filtroSemana === 5) return a.dia >= 29;
    return true;
  }) || [];

  const mainBg = modoImpressao ? 'bg-slate-50' : 'bg-[#0E1218]';
  const cardBg = modoImpressao ? 'bg-white border-slate-200 shadow-sm' : 'bg-[#1A1F2B] border-white/5';
  const itemBg = modoImpressao ? 'bg-slate-50 border-slate-200' : 'bg-[#232936] border-white/5';
  const textColor = modoImpressao ? 'text-slate-800' : 'text-white';
  const textMuted = modoImpressao ? 'text-slate-500' : 'text-slate-400';
  const titleColor = modoImpressao ? 'text-slate-900' : 'text-slate-300';
  const chartText = modoImpressao ? '#64748B' : '#94A3B8';
  const chartGrid = modoImpressao ? '#E2E8F0' : '#2D3342';
  const tooltipBg = modoImpressao ? '#FFFFFF' : '#1E2330';
  const tooltipColor = modoImpressao ? '#0F172A' : '#FFFFFF';

  if (!autenticado) {
    return (
      <div className="min-h-screen bg-[#0E1218] flex items-center justify-center p-4 relative overflow-hidden font-sans">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-blue-500/15 blur-[120px] rounded-full pointer-events-none"></div>
        <div className="max-w-[380px] w-full relative z-10">
          <div className="text-center mb-8">
            <div className="w-12 h-12 bg-[#1A1F2B] border border-white/5 rounded-xl flex items-center justify-center mx-auto mb-6 shadow-xl"><Activity className="text-white w-6 h-6" /></div>
            <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">Welcome back</h2>
            <p className="text-slate-400 text-sm">Dashboard de <span className="text-blue-400 cursor-pointer">RH Analytics</span>.</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-4">
            <div><label className="block text-xs font-medium text-slate-400 mb-1.5 ml-1">Usuário</label><input type="text" value={usuario} onChange={(e) => setUsuario(e.target.value)} className="block w-full px-4 py-3 bg-[#1A1F2B] border border-white/5 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all text-sm" placeholder="Ex: diretoria" required /></div>
            <div><label className="block text-xs font-medium text-slate-400 mb-1.5 ml-1">Senha</label><input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} className="block w-full px-4 py-3 bg-[#1A1F2B] border border-white/5 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all text-sm" placeholder="••••••••" required /></div>
            {erroLogin && <div className="text-red-400 text-sm text-center font-medium pt-2">{erroLogin}</div>}
            <div className="pt-4"><button type="submit" disabled={fazendoLogin} className={`w-full flex justify-center py-3 px-4 rounded-lg shadow-lg text-sm font-semibold text-white transition-all ${fazendoLogin ? 'bg-slate-700 cursor-not-allowed' : 'bg-gradient-to-r from-[#6366F1] to-[#3B82F6] hover:opacity-90'}`}>{fazendoLogin ? 'Autenticando...' : 'Sign in to Dashboard'}</button></div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex h-screen font-sans transition-colors duration-300 ${modoImpressao ? 'bg-slate-100 text-slate-900' : 'bg-[#0E1218] text-white'}`}>
      
      {!modoImpressao && (
        <aside className="w-64 bg-[#0B0F19] border-r border-white/5 flex flex-col hide-on-print">
          <div className="p-6 flex items-center gap-3 border-b border-white/5">
            <Activity className="text-blue-500 w-8 h-8" />
            <span className="text-white font-bold text-xl tracking-wide">RH Analytics</span>
          </div>
          <nav className="flex-1 p-4 space-y-2">
            <button onClick={() => setMenuAtivo("visao_geral")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all text-sm ${menuAtivo === 'visao_geral' ? 'bg-[#1A1F2B] text-white border border-white/5' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><LayoutDashboard className="w-4 h-4" /> Visão Geral</button>
            <button onClick={() => setMenuAtivo("comportamento")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all text-sm ${menuAtivo === 'comportamento' ? 'bg-[#1A1F2B] text-white border border-white/5' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><UsersRound className="w-4 h-4" /> Comportamento e Saúde</button>
            <button onClick={() => setMenuAtivo("desempenho")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all text-sm ${menuAtivo === 'desempenho' ? 'bg-[#1A1F2B] text-white border border-white/5' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><Star className="w-4 h-4" /> Desempenho</button>
          </nav>
          <div className="p-4 border-t border-white/5">
            <button onClick={handleLogout} className="w-full flex items-center justify-center gap-2 px-4 py-2 hover:bg-red-500/10 text-slate-400 hover:text-red-400 rounded-lg transition-colors text-sm font-medium"><Lock className="w-4 h-4" /> Sign out</button>
          </div>
        </aside>
      )}

      <main className={`flex-1 overflow-y-auto ${modoImpressao ? 'p-0' : 'p-8'} ${mainBg}`}>
        
        {!modoImpressao && (
          <header className="flex justify-between items-center mb-8">
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              {menuAtivo === "visao_geral" && `Visão Geral (${NOME_MESES[mesSelecionado-1]} ${anoSelecionado})`}
              {menuAtivo === "comportamento" && `Comportamento e Saúde (${NOME_MESES[mesSelecionado-1]} ${anoSelecionado})`}
              {menuAtivo === "desempenho" && `Performance da Equipe (${anoSelecionado})`}
            </h1>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-[#1A1F2B] border border-white/5 rounded-lg p-1">
                <Calendar className="w-4 h-4 text-slate-400 ml-2" />
                <select value={mesSelecionado} onChange={(e) => setMesSelecionado(Number(e.target.value))} className="bg-transparent text-slate-200 text-sm py-1.5 pl-2 pr-6 outline-none cursor-pointer hover:text-white appearance-none" style={{backgroundImage: 'none'}}>
                  {NOME_MESES.map((nome, index) => (<option key={index} value={index + 1} className="bg-[#1A1F2B] text-white">{nome}</option>))}
                </select>
                <div className="w-px h-4 bg-white/10"></div>
                <select value={anoSelecionado} onChange={(e) => setAnoSelecionado(Number(e.target.value))} className="bg-transparent text-slate-200 text-sm py-1.5 pl-2 pr-6 outline-none cursor-pointer hover:text-white appearance-none" style={{backgroundImage: 'none'}}>
                  <option value={2024} className="bg-[#1A1F2B] text-white">2024</option>
                  <option value={2025} className="bg-[#1A1F2B] text-white">2025</option>
                  <option value={2026} className="bg-[#1A1F2B] text-white">2026</option>
                </select>
              </div>
              <button onClick={exportarPDF} disabled={gerandoPdf} className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer border border-white/5 ${gerandoPdf ? 'bg-slate-800 text-slate-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 text-white border-none'}`}>
                <Download className="w-4 h-4" /> {gerandoPdf ? "Processando Relatório..." : "Gerar Relatório A4"}
              </button>
            </div>
          </header>
        )}

        {/* CONTAINER DO RELATÓRIO COM SPINNER DE CARREGAMENTO */}
        {/* MUDANÇA: O 'w-[1200px] mx-auto' força os gráficos a não bugarem na foto */}
        <div id="area-relatorio" className={`relative ${modoImpressao ? "w-[1200px] mx-auto p-4 space-y-8 bg-slate-50" : "p-2 rounded-lg"}`}>
          
          {carregandoDados && !modoImpressao && (
            <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#0E1218]/60 backdrop-blur-sm rounded-lg">
              <div className="flex flex-col items-center gap-4 bg-[#1A1F2B] p-8 rounded-xl border border-white/10 shadow-2xl">
                <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
                <div className="text-center">
                  <p className="text-white font-bold tracking-wide">Sincronizando Dados</p>
                  <p className="text-slate-400 text-xs mt-1">Conectando ao banco do Notion...</p>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* PÁGINA 1: VISÃO GERAL */}
          {/* ========================================================= */}
          {(menuAtivo === "visao_geral" || modoImpressao) && (
            <div id="print-visao" className={modoImpressao ? `p-8 rounded-xl bg-white border border-slate-200 shadow-sm` : ""}>
              
              <div className={`mb-6 border-b pb-4 ${modoImpressao ? 'border-slate-200' : 'border-white/5'}`}>
                <h2 className={`text-2xl font-bold ${textColor} tracking-tight uppercase`}>1. Sumário Executivo</h2>
                <p className={`${textMuted} text-sm`}>Gerado em: {new Date().toLocaleDateString('pt-BR')} | Ref: {NOME_MESES[mesSelecionado-1]} {anoSelecionado}</p>
              </div>

              <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-blue-500/10 text-blue-500 rounded-lg"><Users className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Ativos</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.funcionarios}</h3></div></div>
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-lg"><UserPlus className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Admissões</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.admissoes}</h3></div></div>
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-rose-500/10 text-rose-500 rounded-lg"><UserMinus className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Desligamentos</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.desligamentos}</h3></div></div>
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-purple-500/10 text-purple-500 rounded-lg"><Activity className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Turnover</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.turnover}</h3></div></div>
              </section>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4 mb-8">
                <div className={`${cardBg} p-6 rounded-xl`}>
                  <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><TrendingDown className="w-4 h-4 text-purple-500" /> Evolução do Turnover</h3>
                  <div className="h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={kpis.graficoTurnover} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartGrid} /><XAxis dataKey="mes" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} /><YAxis axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} tickFormatter={(value) => `${value}%`} /><Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} itemStyle={{color: tooltipColor}} /><Line isAnimationActive={!modoImpressao} type="monotone" dataKey="turnover" name="Turnover %" stroke="#818CF8" strokeWidth={3} dot={{r: 4, fill: '#818CF8', strokeWidth: 2, stroke: modoImpressao ? '#fff' : '#1A1F2B'}} activeDot={{r: 6}} /></LineChart></ResponsiveContainer></div>
                </div>
                <div className={`${cardBg} p-6 rounded-xl`}>
                  <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><UsersRound className="w-4 h-4 text-emerald-500" /> Headcount por Setor</h3>
                  <div className="h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={kpis.graficoHeadcount} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={chartGrid} /><XAxis type="number" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} /><YAxis type="category" dataKey="setor" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 11}} width={80} /><Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} cursor={{fill: chartGrid}} /><Bar isAnimationActive={!modoImpressao} dataKey="quantidade" name="Colaboradores" fill="#34D399" radius={[0, 4, 4, 0]} barSize={20} /></BarChart></ResponsiveContainer></div>
                </div>
                <div className={`${cardBg} p-6 rounded-xl`}>
                  <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><PieChartIcon className="w-4 h-4 text-blue-500" /> Motivos de Desligamento</h3>
                  <div className="h-64 flex justify-center"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie isAnimationActive={!modoImpressao} data={kpis.graficoMotivos} innerRadius={60} outerRadius={85} paddingAngle={5} dataKey="value" stroke="none">{kpis.graficoMotivos.map((entry, index) => (<Cell key={`cell-${index}`} fill={CORES_DONUT[index % CORES_DONUT.length]} />))}</Pie><Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} itemStyle={{color: tooltipColor}} /><Legend iconType="circle" wrapperStyle={{fontSize: '12px', color: chartText}} /></PieChart></ResponsiveContainer></div>
                </div>
                <div className={`${cardBg} p-6 rounded-xl`}>
                  <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Activity className="w-4 h-4 text-rose-500" /> Absenteísmo por Setor</h3>
                  <div className="h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={kpis.graficoSetores} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartGrid} /><XAxis dataKey="setor" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} /><YAxis axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} /><Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} cursor={{fill: chartGrid}} /><Legend iconType="circle" wrapperStyle={{fontSize: '12px', paddingTop: '10px', color: chartText}} /><Bar isAnimationActive={!modoImpressao} dataKey="faltas" name="Faltas" fill="#F43F5E" radius={[4, 4, 0, 0]} /><Bar isAnimationActive={!modoImpressao} dataKey="atestados" name="Atestados" fill="#FBBF24" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div>
                </div>
              </div>

              {/* ALERTAS INTELIGENTES */}
              <div className={`border-t ${modoImpressao ? 'border-slate-200' : 'border-white/5'} pt-8 mt-4`}>
                <h2 className={`text-xl font-bold ${textColor} tracking-tight mb-6 flex items-center gap-3`}>Alertas Operacionais & Clima</h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className={`${cardBg} p-6 rounded-xl flex flex-col h-full`}>
                    <div className="flex justify-between items-center mb-6">
                      <h3 className={`text-sm font-bold ${titleColor} flex items-center gap-2 uppercase tracking-wider`}><Gift className="w-4 h-4 text-amber-500" /> Aniversariantes</h3>
                    </div>
                    <div className="space-y-3 flex-1 overflow-y-auto max-h-64 pr-2 custom-scrollbar">
                      {aniversariosFiltrados.length > 0 ? (
                        aniversariosFiltrados.map((pessoa: any, idx: number) => (
                          <div key={idx} className={`flex justify-between items-center ${itemBg} p-3 rounded-lg border`}>
                            <span className={`text-sm font-medium ${textColor}`}>{pessoa.nome}</span>
                            <span className={`text-amber-600 text-xs font-bold px-2 py-1 ${modoImpressao ? 'bg-amber-100' : 'bg-amber-400/10 text-amber-400'} rounded-md`}>Dia {pessoa.dia}</span>
                          </div>
                        ))
                      ) : (<p className={`text-sm ${textMuted} italic p-3 ${modoImpressao ? 'bg-slate-50' : 'bg-[#232936]/50'} rounded-lg border border-dashed text-center mt-4`}>Nenhum aniversariante.</p>)}
                    </div>
                  </div>

                  <div className={`${cardBg} p-6 rounded-xl flex flex-col h-full`}>
                    <div className="flex justify-between items-center mb-6 relative z-10">
                      <h3 className={`text-sm font-bold ${titleColor} flex items-center gap-2 uppercase tracking-wider`}><BellRing className="w-4 h-4 text-rose-500" /> Experiência</h3>
                    </div>
                    <div className="space-y-3 relative z-10 flex-1 overflow-y-auto max-h-64 pr-2 custom-scrollbar">
                      {contratosFiltrados.length > 0 ? (
                        contratosFiltrados.map((pessoa: any, idx: number) => {
                          const tagUrgencia = verificarUrgencia(pessoa.dia);
                          const isUrgente = tagUrgencia !== null;
                          return (
                            <div key={idx} className={`flex justify-between items-center p-3 rounded-lg border ${isUrgente ? (modoImpressao ? 'bg-red-50 border-red-200' : 'bg-red-500/10 border-red-500/30') : `${itemBg} border-l-2 ${modoImpressao ? 'border-l-rose-500' : 'border-l-rose-500'}`}`}>
                              <div className="flex flex-col">
                                <span className={`text-sm font-medium ${isUrgente ? 'text-red-500' : textColor}`}>{pessoa.nome}</span>
                                {isUrgente && <span className="text-[10px] text-red-500 font-bold mt-0.5 flex items-center gap-1"><AlertTriangle className="w-3 h-3"/> {tagUrgencia}</span>}
                              </div>
                              <span className={`${isUrgente ? (modoImpressao ? 'text-red-600 bg-red-100' : 'text-red-400 bg-red-400/10') : (modoImpressao ? 'text-rose-600 bg-rose-100' : 'text-rose-400 bg-rose-400/10')} text-xs font-bold px-2 py-1 rounded-md`}>Dia {pessoa.dia}</span>
                            </div>
                          )
                        })
                      ) : (<p className={`text-sm ${textMuted} italic p-3 ${modoImpressao ? 'bg-slate-50' : 'bg-[#232936]/50'} rounded-lg border border-dashed text-center mt-4`}>Nenhum contrato vencendo.</p>)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* PÁGINA 2: COMPORTAMENTO DISCIPLINA E SAÚDE */}
          {/* ========================================================= */}
          {(menuAtivo === "comportamento" || modoImpressao) && (
            <div id="print-comportamento" className={modoImpressao ? `p-8 rounded-xl bg-white border border-slate-200 shadow-sm` : ""}>
              
              {modoImpressao && (
                <div className="mb-6 border-b pb-4 border-slate-200">
                  <h2 className={`text-2xl font-bold ${textColor} tracking-tight uppercase`}>2. Saúde Ocupacional & Comportamento</h2>
                  <p className={`${textMuted} text-sm`}>Gerado em: {new Date().toLocaleDateString('pt-BR')} | Ref: {NOME_MESES[mesSelecionado-1]} {anoSelecionado}</p>
                </div>
              )}

              <section className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-amber-500/10 text-amber-500 rounded-lg"><Stethoscope className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Atestados</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.atestados}</h3></div></div>
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-orange-500/10 text-orange-500 rounded-lg"><AlertOctagon className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Advertências</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.advertencias}</h3></div></div>
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-rose-500/10 text-rose-500 rounded-lg"><Clock className="w-6 h-6" /></div><div className="flex-1"><p className={`text-xs ${textMuted} font-bold uppercase mb-1`}>Frequência</p><div className="flex items-center gap-6"><div><span className={`text-2xl font-bold ${textColor}`}>{kpis.faltas}</span><span className={`text-[10px] ${textMuted} ml-1 font-bold uppercase`}>Faltas</span></div><div className={`w-px h-8 ${modoImpressao ? 'bg-slate-200' : 'bg-white/10'}`}></div><div><span className={`text-2xl font-bold ${textColor}`}>{kpis.atrasos}</span><span className={`text-[10px] ${textMuted} ml-1 font-bold uppercase`}>Atrasos</span></div></div></div></div>
                <div className={`${cardBg} border-red-200 p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-red-500/10 text-red-500 rounded-lg z-10"><DollarSign className="w-6 h-6" /></div><div className="z-10"><p className="text-xs text-red-500 font-bold uppercase mb-1">Impacto Financeiro</p><h3 className={`text-2xl font-bold ${textColor}`}>{formatarMoeda(kpis.custo_absenteismo)}</h3></div></div>
              </section>

              {/* GRÁFICOS: MÉDICOS E CIDs */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                <div className={`${cardBg} p-6 rounded-xl`}>
                  <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Stethoscope className="w-4 h-4 text-emerald-500" /> Médicos Emissores (Top 7)</h3>
                  <div className="h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={kpis.rankingMedicos} layout="vertical" margin={{ top: 5, right: 20, left: 60, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={chartGrid} /><XAxis type="number" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} /><YAxis type="category" dataKey="nome" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 11}} width={120} /><Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} cursor={{fill: chartGrid}} /><Bar isAnimationActive={!modoImpressao} dataKey="quantidade" name="Atestados" fill="#10B981" radius={[0, 4, 4, 0]} barSize={16} /></BarChart></ResponsiveContainer></div>
                </div>
                <div className={`${cardBg} p-6 rounded-xl`}>
                  <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Activity className="w-4 h-4 text-rose-500" /> CIDs Mais Frequentes (Top 10)</h3>
                  <div className="h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={kpis.rankingCids} layout="vertical" margin={{ top: 5, right: 20, left: 100, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={chartGrid} /><XAxis type="number" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} /><YAxis type="category" dataKey="nome" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 11}} width={160} /><Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} cursor={{fill: chartGrid}} /><Bar isAnimationActive={!modoImpressao} dataKey="quantidade" name="Ocorrências" fill="#F43F5E" radius={[0, 4, 4, 0]} barSize={16} /></BarChart></ResponsiveContainer></div>
                </div>
              </div>

              {/* GRÁFICOS: RANKINGS */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                <div className={`${cardBg} p-6 rounded-xl flex flex-col`}>
                  <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><TrendingDown className="w-4 h-4 text-rose-500" /> Ofensores de Faltas (Top 5)</h3>
                  <div className="space-y-3 flex-1 overflow-y-auto max-h-64 pr-2 custom-scrollbar">
                    {kpis.rankingFaltas?.length > 0 ? (
                      kpis.rankingFaltas.map((pessoa: any, idx: number) => (
                        <div key={idx} className={`flex justify-between items-center ${itemBg} p-3 rounded-lg border`}>
                          <div className="flex items-center gap-3"><span className={`w-6 h-6 flex items-center justify-center rounded-full ${modoImpressao ? 'bg-slate-200' : 'bg-slate-800'} text-xs font-bold ${textMuted}`}>{idx + 1}º</span><span className={`text-sm font-medium ${textColor}`}>{pessoa.nome}</span></div>
                          <span className={`${modoImpressao ? 'text-rose-600 bg-rose-100' : 'text-rose-400 bg-rose-400/10'} text-xs font-bold px-2 py-1 rounded-md`}>{pessoa.faltas} dias</span>
                        </div>
                      ))
                    ) : (<p className={`text-sm ${textMuted} italic p-3 ${modoImpressao ? 'bg-slate-50' : 'bg-[#232936]/50'} rounded-lg border border-dashed text-center mt-4`}>Nenhuma falta registrada.</p>)}
                  </div>
                </div>
                <div className={`${cardBg} p-6 rounded-xl flex flex-col`}>
                  <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Stethoscope className="w-4 h-4 text-emerald-500" /> Volume de Atestados (Top 5)</h3>
                  <div className="space-y-3 flex-1 overflow-y-auto max-h-64 pr-2 custom-scrollbar">
                    {kpis.rankingAtestados?.length > 0 ? (
                      kpis.rankingAtestados.map((pessoa: any, idx: number) => (
                        <div key={idx} className={`flex justify-between items-center ${itemBg} p-3 rounded-lg border`}>
                          <div className="flex items-center gap-3"><span className={`w-6 h-6 flex items-center justify-center rounded-full ${modoImpressao ? 'bg-slate-200' : 'bg-slate-800'} text-xs font-bold ${textMuted}`}>{idx + 1}º</span><span className={`text-sm font-medium ${textColor}`}>{pessoa.nome}</span></div>
                          <span className={`${modoImpressao ? 'text-emerald-700 bg-emerald-100' : 'text-emerald-400 bg-emerald-400/10'} text-xs font-bold px-2 py-1 rounded-md`}>{pessoa.atestados} atestados</span>
                        </div>
                      ))
                    ) : (<p className={`text-sm ${textMuted} italic p-3 ${modoImpressao ? 'bg-slate-50' : 'bg-[#232936]/50'} rounded-lg border border-dashed text-center mt-4`}>Nenhum atestado registrado.</p>)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* PÁGINA 3: DESEMPENHO E AVALIAÇÕES */}
          {/* ========================================================= */}
          {(menuAtivo === "desempenho" || modoImpressao) && (
            <div id="print-desempenho" className={modoImpressao ? `p-8 rounded-xl bg-white border border-slate-200 shadow-sm` : ""}>
              
              {modoImpressao && (
                <div className="mb-6 border-b pb-4 border-slate-200">
                  <h2 className={`text-2xl font-bold ${textColor} tracking-tight uppercase`}>3. Performance e Produtividade</h2>
                  <p className={`${textMuted} text-sm`}>Gerado em: {new Date().toLocaleDateString('pt-BR')} | Ref: {NOME_MESES[mesSelecionado-1]} {anoSelecionado}</p>
                </div>
              )}

              <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-indigo-500/10 text-indigo-500 rounded-lg"><Star className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Avaliações Realizadas</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.avaliacoes}</h3></div></div>
              </section>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
                <div className={`${cardBg} p-6 rounded-xl`}>
                  <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Activity className="w-4 h-4 text-indigo-500" /> Mapa de Competências (Média)</h3>
                  <div className="h-72 flex justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" outerRadius="80%" data={kpis.graficoRadar}>
                        <PolarGrid stroke={chartGrid} />
                        <PolarAngleAxis dataKey="subject" tick={{fill: chartText, fontSize: 11}} />
                        <PolarRadiusAxis angle={30} domain={[0, 5]} tick={false} axisLine={false} />
                        <Radar isAnimationActive={!modoImpressao} name="Média Geral" dataKey="A" stroke="#818CF8" fill="#818CF8" fillOpacity={0.4} />
                        <Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
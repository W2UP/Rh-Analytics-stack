import { apiFetch } from './api';
import { useDashboard } from './hooks/useDashboard';
import { IndicadorDetalhes } from './components/IndicadorDetalhes';
import { FolhaVersoes } from './components/FolhaVersoes';
import { useState, useEffect } from 'react';
import { LayoutDashboard, Users, UserPlus, UserMinus, Activity, Stethoscope, AlertOctagon, Clock, Star, UsersRound, Download, TrendingDown, Lock, PieChart as PieChartIcon, DollarSign, Calendar, Gift, BellRing, AlertTriangle, Loader2, X, Briefcase, HeartPulse, Wallet, CalendarRange, Flame, Package, LockKeyhole, Unlock, Wrench, UploadCloud, RefreshCw, CheckCircle2, Bot, ShoppingCart, Pill, Award } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, LabelList } from 'recharts';

const CORES_DONUT = ['#818CF8', '#F43F5E', '#34D399', '#FBBF24', '#A78BFA', '#F472B6'];
const NOME_MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

export function App() {
  const [autenticado, setAutenticado] = useState(false);
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erroLogin, setErroLogin] = useState("");
  const [fazendoLogin, setFazendoLogin] = useState(false);

  const [verificandoSessao, setVerificandoSessao] = useState(true);
  const [indicadorAberto, setIndicadorAberto] = useState<"funcionarios" | "admissoes" | "desligamentos" | null>(null);
  
  const [mesSelecionado, setMesSelecionado] = useState(new Date().getMonth() + 1); 
  const [anoSelecionado, setAnoSelecionado] = useState(new Date().getFullYear()); 
  const [setorSelecionado, setSetorSelecionado] = useState("Todos");

  const [filtroContrato, setFiltroContrato] = useState("45 Dias"); 
  const [filtroSemana, setFiltroSemana] = useState(0); 
  const [modoImpressao, setModoImpressao] = useState(false);
  const [modal360, setModal360] = useState<string | null>(null);

  // ESTADOS DA TELA DE FOLHA
  const [modoFolha, setModoFolha] = useState<'calculo' | 'rpa' | 'vales' | 'convocacao' | 'farmacia' | 'auditor' | 'bonus' | 'auditor_bonus'>('calculo');
  
  const [processandoPonto, setProcessandoPonto] = useState(false);
  const [resultadoPonto, setResultadoPonto] = useState<any[]>([]);
  const [erroPonto, setErroPonto] = useState("");
  const [salvandoFolha, setSalvandoFolha] = useState(false);
  const [mensagemFolha, setMensagemFolha] = useState("");

  const [arquivoSapRpa, setArquivoSapRpa] = useState<File | null>(null);
  const [arquivoBaseRpa, setArquivoBaseRpa] = useState<File | null>(null);
  const [gerandoRpa, setGerandoRpa] = useState(false);

  const [arquivoDashboard, setArquivoDashboard] = useState<File | null>(null);
  const [processandoDashboard, setProcessandoDashboard] = useState(false);
  const [dadosHorasExtras, setDadosHorasExtras] = useState<any>(null);

  const [arquivoPdfConvocacao, setArquivoPdfConvocacao] = useState<File | null>(null);
  const [processandoConvocacao, setProcessandoConvocacao] = useState(false);
  const [resultadoConvocacao, setResultadoConvocacao] = useState<any>(null);

  const [arquivoPdfVale, setArquivoPdfVale] = useState<File | null>(null);
  const [processandoVale, setProcessandoVale] = useState(false);
  const [dadosPreLista, setDadosPreLista] = useState<any>(null);
  const [nomeEditado, setNomeEditado] = useState("");
  const [valorEditado, setValorEditado] = useState("");

  const [arquivoExtratoFarmacia, setArquivoExtratoFarmacia] = useState<File | null>(null);
  const [processandoFarmacia, setProcessandoFarmacia] = useState(false);

  const [arquivoPdfHolerite, setArquivoPdfHolerite] = useState<File | null>(null);
  const [processandoAuditoria, setProcessandoAuditoria] = useState(false);
  const [resultadoAuditoria, setResultadoAuditoria] = useState<any>(null);

  // ESTADOS DO AUDITOR DE BÔNUS (PDF UCHOA)
  const [arquivoPdfBonus, setArquivoPdfBonus] = useState<File | null>(null);
  const [processandoAuditoriaBonus, setProcessandoAuditoriaBonus] = useState(false);
  const [resultadoAuditoriaBonus, setResultadoAuditoriaBonus] = useState<any>(null);

  const { kpis, carregandoDados, sincronizando, erroDados, syncStatus, carregarDadosDashboard, forcarSincronizacao } = useDashboard(autenticado, mesSelecionado, anoSelecionado, setorSelecionado);

  const [menuAtivo, setMenuAtivo] = useState("visao_geral");
  const [gerandoPdf, setGerandoPdf] = useState(false);

  useEffect(() => {
    localStorage.removeItem('rh_logado');
    apiFetch('/session').then(() => setAutenticado(true)).catch(() => setAutenticado(false)).finally(() => setVerificandoSessao(false));
    const expired = () => { setAutenticado(false); setIndicadorAberto(null); setErroLogin('Sua sessão expirou. Entre novamente.'); };
    window.addEventListener('rh:session-expired', expired);
    return () => window.removeEventListener('rh:session-expired', expired);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault(); setFazendoLogin(true); setErroLogin("");
    try {
      const resposta = await apiFetch("/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario, senha }) });
      const dados = await resposta.json();
      if (dados.sucesso) { setAutenticado(true); setSenha(""); } 
      else { setErroLogin("Usuário ou senha incorretos."); }
    } catch (erro) { setErroLogin((erro as Error).message || "Não foi possível entrar."); } 
    finally { setFazendoLogin(false); }
  };

  const handleLogout = async () => {
    try { await apiFetch('/logout', { method: 'POST' }); setAutenticado(false); setIndicadorAberto(null); }
    catch (e) { setErroLogin((e as Error).message); alert('Não foi possível encerrar a sessão no servidor. Tente novamente.'); }
  };
  
  const formatarMoeda = (valor: number | string) => {
    if (valor === "-" || isNaN(Number(valor))) return "R$ 0,00";
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor));
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setProcessandoPonto(true); setErroPonto(""); setResultadoPonto([]);
    const formData = new FormData(); formData.append("arquivo", file);
    try {
      const response = await apiFetch("/processar_ponto", { method: "POST", body: formData });
      const data = await response.json();
      if (data.sucesso) { setResultadoPonto(data.dados); } else { setErroPonto(data.erro || "Falha ao processar o arquivo SAP."); }
    } catch (err) { setErroPonto("Erro de conexão. O servidor Python está rodando?"); } 
    finally { setProcessandoPonto(false); }
  };

  const handleSalvarFolha = async () => {
    if (resultadoPonto.length === 0) return;
    setSalvandoFolha(true); setMensagemFolha("");
    try {
      const payload = { mes: mesSelecionado, ano: anoSelecionado, lancamentos: resultadoPonto };
      const resposta = await apiFetch("/salvar_folha", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const dados = await resposta.json();
      if (dados.sucesso) {
        setMensagemFolha("✅ Salvo com sucesso! Histórico auditável gerado.");
        setTimeout(() => { setResultadoPonto([]); setMensagemFolha(""); carregarDadosDashboard(); }, 3000);
      } else { setMensagemFolha(`❌ Erro ao salvar: ${dados.erro}`); }
    } catch (err) { setMensagemFolha("❌ Erro de conexão com o servidor Python."); } 
    finally { setSalvandoFolha(false); }
  };

  const handleGerarRPA = async () => {
    if (!arquivoSapRpa || !arquivoBaseRpa) {
      alert("Por favor, anexe os dois arquivos para iniciar o RPA.");
      return;
    }
    setGerandoRpa(true);
    const formData = new FormData();
    formData.append("arquivo_sap", arquivoSapRpa);
    formData.append("arquivo_escritorio", arquivoBaseRpa);

    try {
        const response = await apiFetch("/rpa_horas_extras", { method: "POST", body: formData });
        if (response.ok) {
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                const errData = await response.json();
                alert("❌ Erro no Servidor: " + errData.erro);
            } else {
                const proc = response.headers.get("X-Processados") || "0";
                const erros = response.headers.get("X-Nao-Encontrados") || "Nenhum";

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "ESCRITORIO_PRONTO.xlsx";
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                
                let msg = `✅ Sucesso! Foram lançados os dados de ${proc} colaboradores.`;
                if (erros !== "Nenhum") {
                    const listaErros = erros.split("|").join("\n- ");
                    msg += `\n\n⚠️ ATENÇÃO: As seguintes pessoas tinham horas extras ou faltas no SAP, mas NÃO foram encontradas na planilha da contabilidade:\n- ${listaErros}\n\nEles podem ter sido desligados, ou o nome está diferente no Excel.`;
                }
                alert(msg);
            }
        } else { alert("❌ Falha de comunicação com o Robô RPA."); }
    } catch(e) { alert("❌ Erro técnico: " + e); } 
    finally { setGerandoRpa(false); }
  }

  const handleGerarRpaBonus = async () => {
    if (!arquivoSapRpa || !arquivoBaseRpa) {
      alert("Por favor, anexe o arquivo do SAP (.xls) e a Planilha de Bônus.");
      return;
    }
    setGerandoRpa(true);
    
    const formData = new FormData();
    formData.append("arquivo_sap", arquivoSapRpa);
    formData.append("arquivo_planilha", arquivoBaseRpa);

    try {
      const response = await apiFetch("/rpa_bonus", { method: "POST", body: formData });
      
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const errData = await response.json();
        alert("❌ " + errData.erro);
      } else {
        const proc = response.headers.get("X-Processados") || "0";
        const erros = response.headers.get("X-Nao-Encontrados") || "Nenhum";
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "BONUS_PROCESSADO.xlsx";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        let msg = `✅ Sucesso! Os percentuais de desconto foram aplicados para ${proc} colaboradores.`;
        if (erros !== "Nenhum") {
            const listaErros = erros.split("|").join("\n- ");
            msg += `\n\n⚠️ ATENÇÃO: As seguintes pessoas sofreram descontos de bônus no SAP, mas não foram encontradas na sua planilha:\n- ${listaErros}`;
        }
        alert(msg);
      }
    } catch(e) {
      alert("❌ Erro técnico: " + e);
    } finally {
      setGerandoRpa(false);
    }
  };

  const handleAtualizarDashboardHoras = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setArquivoDashboard(file);
    setProcessandoDashboard(true);
    
    const formData = new FormData();
    formData.append("arquivo_sap", file);

    try {
      const response = await apiFetch("/dashboard_tempo_real", {
        method: "POST",
        body: formData
      });
      
      const data = await response.json();
      
      if (data.sucesso) {
        setDadosHorasExtras(data);
      } else {
        alert("Falha ao processar dashboard de horas: " + (data.erro || "Erro desconhecido"));
      }
    } catch (err) {
      alert("Erro de conexão. O servidor Python está rodando?");
    } finally {
      setProcessandoDashboard(false);
    }
  };

  const handleAuditarConvocacao = async () => {
    if (!arquivoPdfConvocacao || !arquivoSapRpa) {
      alert("Por favor, anexe o PDF do Termo Assinado e o Excel do SAP.");
      return;
    }
    setProcessandoConvocacao(true);
    setResultadoConvocacao(null);
    
    const formData = new FormData();
    formData.append("arquivo_pdf", arquivoPdfConvocacao);
    formData.append("arquivo_sap", arquivoSapRpa);

    try {
      const response = await apiFetch("/auditar_convocacao", { method: "POST", body: formData });
      const data = await response.json();
      if (data.sucesso) {
        setResultadoConvocacao(data);
      } else {
        alert("Erro na Auditoria: " + data.erro);
      }
    } catch (e) {
      alert("Erro de conexão com o Servidor Python.");
    } finally {
      setProcessandoConvocacao(false);
    }
  };

  const handleExtrairVales = async () => {
    if (!arquivoPdfVale) {
      alert("Anexe o PDF do Romaneio primeiro.");
      return;
    }
    setProcessandoVale(true);
    setDadosPreLista(null);
    
    const formData = new FormData();
    formData.append("arquivo_pdf", arquivoPdfVale);

    try {
      const response = await apiFetch("/extrair_vales", { method: "POST", body: formData });
      const data = await response.json();
      if (data.sucesso) {
        setDadosPreLista(data);
        setNomeEditado(data.cliente_lido);
        setValorEditado(data.valor_calculado);
      } else {
        alert("❌ Erro ao ler PDF: " + data.erro);
      }
    } catch(e) {
      alert("❌ Erro técnico: " + e);
    } finally {
      setProcessandoVale(false);
    }
  };

  const handleInjetarValesConfirmados = async () => {
    if (!arquivoBaseRpa) {
      alert("Anexe a Planilha da Contabilidade primeiro.");
      return;
    }
    setProcessandoVale(true);
    
    const formData = new FormData();
    formData.append("arquivo_escritorio", arquivoBaseRpa);
    formData.append("cliente_nome", nomeEditado);
    formData.append("valor_desconto", valorEditado);

    try {
      const response = await apiFetch("/injetar_vales", { method: "POST", body: formData });
      
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const errData = await response.json();
        alert("❌ " + errData.erro);
      } else {
        const funcNome = response.headers.get("X-Funcionario-Nome") || "Funcionário";
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `ESCRITORIO_VALES_${funcNome}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        alert(`✅ Sucesso! Lançado na linha exata de: ${funcNome}`);
        setDadosPreLista(null);
      }
    } catch(e) {
      alert("❌ Erro técnico: " + e);
    } finally {
      setProcessandoVale(false);
    }
  };

  const handleGerarRpaFarmacia = async () => {
    if (!arquivoExtratoFarmacia || !arquivoBaseRpa) {
      alert("Por favor, anexe o Arquivo de Extrato da Farmácia (.xls) e a Planilha da Contabilidade.");
      return;
    }
    setProcessandoFarmacia(true);
    
    const formData = new FormData();
    formData.append("arquivo_extrato", arquivoExtratoFarmacia);
    formData.append("arquivo_escritorio", arquivoBaseRpa);

    try {
      const response = await apiFetch("/rpa_farmacia", { method: "POST", body: formData });
      
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const errData = await response.json();
        alert("❌ " + errData.erro);
      } else {
        const proc = response.headers.get("X-Processados") || "0";
        const erros = response.headers.get("X-Nao-Encontrados") || "Nenhum";
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "ESCRITORIO_FARMACIA_PRONTO.xlsx";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        let msg = `✅ Sucesso! Foram lançados os descontos de ${proc} colaboradores.`;
        if (erros !== "Nenhum") {
            const listaErros = erros.split("|").join("\n- ");
            msg += `\n\n⚠️ ATENÇÃO: Os seguintes nomes estavam no arquivo da farmácia mas não foram encontrados na sua planilha:\n- ${listaErros}`;
        }
        alert(msg);
      }
    } catch(e) {
      alert("❌ Erro técnico: " + e);
    } finally {
      setProcessandoFarmacia(false);
    }
  };

  const handleAuditarFolha = async () => {
    if (!arquivoPdfHolerite || !arquivoBaseRpa) {
      alert("Anexe o PDF dos Holerites e a Planilha da Contabilidade.");
      return;
    }
    setProcessandoAuditoria(true);
    setResultadoAuditoria(null);
    
    const formData = new FormData();
    formData.append("arquivo_pdf", arquivoPdfHolerite);
    formData.append("arquivo_escritorio", arquivoBaseRpa);

    try {
      const response = await apiFetch("/auditar_folha", { method: "POST", body: formData });
      const data = await response.json();
      if (data.sucesso) {
        setResultadoAuditoria(data);
      } else {
        alert("❌ Erro ao auditar: " + data.erro);
      }
    } catch(e) {
      alert("❌ Erro técnico: " + e);
    } finally {
      setProcessandoAuditoria(false);
    }
  };

 const handleAuditarBonusUniversal = async () => {
    if (!arquivoPdfBonus || !arquivoBaseRpa) {
      alert("Anexe o Espelho de Ponto do SAP (PDF ou XLS) e a Planilha de Bônus.");
      return;
    }
    setProcessandoAuditoriaBonus(true);
    setResultadoAuditoriaBonus(null);
    
    const formData = new FormData();
    formData.append("arquivo_sap", arquivoPdfBonus);
    formData.append("arquivo_planilha", arquivoBaseRpa);

    try {
      const response = await apiFetch("/auditar_bonus_universal", { method: "POST", body: formData });
      const data = await response.json();
      if (data.sucesso) {
        setResultadoAuditoriaBonus(data);
      } else {
        alert("❌ Erro ao auditar: " + data.erro);
      }
    } catch(e) {
      alert("❌ Erro técnico: " + e);
    } finally {
      setProcessandoAuditoriaBonus(false);
    }
  };
  
  const exportarPDF = async () => {
    const [{ default: html2canvas }, { jsPDF }] = await Promise.all([import('html2canvas-pro'), import('jspdf')]);
    if (kpis.funcionarios === "-") { alert("Aguarde os dados carregarem."); return; }
    try {
      setGerandoPdf(true); setModoImpressao(true); 
      await new Promise((resolve) => setTimeout(resolve, 2000)); 
      
      const pdf = new jsPDF('l', 'mm', 'a4'); 
      const pdfWidth = pdf.internal.pageSize.getWidth(); 
      const pdfPageHeight = pdf.internal.pageSize.getHeight(); 
      
      const paginas = ['print-visao', 'print-comportamento', 'print-ranking-faltas', 'print-ranking-atestados', 'print-ranking-advertencias'];

      let primeiraPagina = true;

      for (const pageId of paginas) {
        const element = document.getElementById(pageId);
        if (element) {
          const canvas = await html2canvas(element, { scale: 2, useCORS: true, backgroundColor: "#F8FAFC", windowWidth: 1200 });
          if (canvas.width === 0) continue; 
          
          const imgData = canvas.toDataURL('image/png');
          const margem = 10;
          const maxImgWidth = pdfWidth - (margem * 2);
          const maxImgHeight = pdfPageHeight - (margem * 2);
          
          let imgWidth = maxImgWidth;
          let imgHeight = (canvas.height * imgWidth) / canvas.width;
          
          if (imgHeight > maxImgHeight) {
            imgHeight = maxImgHeight;
            imgWidth = (canvas.width * imgHeight) / canvas.height;
          }
          
          const marginX = (pdfWidth - imgWidth) / 2;
          const marginY = (pdfPageHeight - imgHeight) / 2;
          
          if (!primeiraPagina) { pdf.addPage(); }
          pdf.addImage(imgData, 'PNG', marginX, marginY, imgWidth, imgHeight);
          primeiraPagina = false;
        }
      }
      pdf.save(`Relatorio_RH_${setorSelecionado !== 'Todos' ? setorSelecionado : 'Geral'}_${NOME_MESES[mesSelecionado-1]}_${anoSelecionado}.pdf`);
    } catch (erro: any) { alert(`Erro ao gerar PDF: ${erro.message}`); } 
    finally { setModoImpressao(false); setGerandoPdf(false); }
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

  const getIniciais = (nome: string) => {
    const partes = nome.split(" ");
    if (partes.length >= 2) return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
    return nome.substring(0, 2).toUpperCase();
  };

  if (verificandoSessao) return <main className="min-h-screen bg-slate-950 text-white grid place-items-center">Verificando acesso…</main>;

  if (!autenticado) {
    return (
      <div className="min-h-screen bg-[#0E1218] flex items-center justify-center p-4 relative overflow-hidden font-sans">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-blue-500/15 blur-[120px] rounded-full pointer-events-none"></div>
        <div className="max-w-[380px] w-full relative z-10">
          <div className="text-center mb-8">
            <div className="w-12 h-12 bg-[#1A1F2B] border border-white/5 rounded-xl flex items-center justify-center mx-auto mb-6 shadow-xl"><Activity className="text-white w-6 h-6" /></div>
            <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">Folha Analytics</h2>
            <p className="text-slate-400 text-sm">Dashboard de <span className="text-blue-400 cursor-pointer">ERP & RH</span>.</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-4">
            <div><label className="block text-xs font-medium text-slate-400 mb-1.5 ml-1">Usuário</label><input type="text" value={usuario} onChange={(e) => setUsuario(e.target.value)} className="block w-full px-4 py-3 bg-[#1A1F2B] border border-white/5 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all text-sm" placeholder="Ex: diretoria" required /></div>
            <div><label className="block text-xs font-medium text-slate-400 mb-1.5 ml-1">Senha</label><input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} className="block w-full px-4 py-3 bg-[#1A1F2B] border border-white/5 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all text-sm" placeholder="••••••••" required /></div>
            {erroLogin && <div className="text-red-400 text-sm text-center font-medium pt-2">{erroLogin}</div>}
            <div className="pt-4"><button type="submit" disabled={fazendoLogin} className={`w-full flex justify-center py-3 px-4 rounded-lg shadow-lg text-sm font-semibold text-white transition-all ${fazendoLogin ? 'bg-slate-700 cursor-not-allowed' : 'bg-gradient-to-r from-[#6366F1] to-[#3B82F6] hover:opacity-90'}`}>{fazendoLogin ? 'Autenticando...' : 'Entrar no painel'}</button></div>
          </form>
        </div>
      </div>
    );
  }

  const perfilInfo = modal360 && kpis.perfis360 ? kpis.perfis360[modal360] : null;
  const armariosReais = kpis.armarios || [];
  const totalArmarios = armariosReais.length;
  const ocupados = armariosReais.filter((a:any) => a.status === "Ocupado").length;
  const livres = armariosReais.filter((a:any) => a.status === "Livre").length;
  const manutencao = armariosReais.filter((a:any) => a.status === "Manutenção").length;

  return (
    <div className={`flex h-screen font-sans transition-colors duration-300 ${modoImpressao ? 'bg-slate-100 text-slate-900' : 'bg-[#0E1218] text-white'}`}>
      
      {!modoImpressao && modal360 && (
        <div className="fixed inset-0 z-[100] flex justify-end overflow-hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm cursor-pointer transition-opacity" onClick={() => setModal360(null)}></div>
          <div className="relative w-full max-w-md bg-[#0F131A] border-l border-white/10 h-full shadow-2xl flex flex-col transform transition-transform duration-300 translate-x-0">
            <div className="p-6 bg-[#1A1F2B] border-b border-white/10 relative">
              <button onClick={() => setModal360(null)} className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-full transition-colors"><X className="w-5 h-5" /></button>
              <div className="flex items-center gap-4 mt-2">
                <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-xl font-bold text-white shadow-lg border-2 border-white/10">{getIniciais(modal360)}</div>
                <div>
                  <h2 className="text-xl font-bold text-white">{modal360}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs font-medium text-slate-400 bg-black/20 px-2 py-0.5 rounded border border-white/5">{perfilInfo?.cargo || "-"}</span>
                    <span className="text-xs font-medium text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">{perfilInfo?.setor || "-"}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#1A1F2B] p-4 rounded-xl border border-white/5 flex flex-col justify-center">
                  <span className="text-[10px] text-slate-400 font-bold uppercase mb-1 flex items-center gap-1.5"><Briefcase className="w-3 h-3 text-emerald-400"/> Tempo de Casa</span>
                  <span className="text-sm font-semibold text-white">{perfilInfo?.tempo_casa || "-"}</span>
                </div>
                <div className="bg-[#1A1F2B] p-4 rounded-xl border border-white/5 flex flex-col justify-center">
                  <span className="text-[10px] text-slate-400 font-bold uppercase mb-1 flex items-center gap-1.5"><Star className="w-3 h-3 text-amber-400"/> Desempenho</span>
                  <span className="text-xl font-bold text-amber-400">{perfilInfo?.nota_desempenho ? Number(perfilInfo.nota_desempenho).toFixed(1) : "-"} <span className="text-xs text-slate-500 font-medium">/ 5.0</span></span>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2"><AlertOctagon className="w-4 h-4 text-orange-400"/> Frequência e Disciplina</h3>
                <div className="bg-[#1A1F2B] rounded-xl border border-white/5 overflow-hidden">
                  <div className="flex justify-between p-3 border-b border-white/5 bg-black/10"><span className="text-sm text-slate-300">Faltas Injustificadas</span><span className="text-sm font-bold text-rose-400">{perfilInfo?.faltas_dias || 0} dias</span></div>
                  <div className="flex justify-between p-3 border-b border-white/5"><span className="text-sm text-slate-300">Atrasos Registrados</span><span className="text-sm font-bold text-orange-400">{perfilInfo?.atrasos || 0}</span></div>
                  <div className="p-3"><span className="text-sm text-slate-300 block mb-2">Advertências ({perfilInfo?.historico_advertencias?.length || 0})</span>
                    {perfilInfo?.historico_advertencias?.length > 0 ? (
                      <div className="space-y-2">{perfilInfo.historico_advertencias.map((adv: any, i: number) => (<div key={i} className="text-xs flex justify-between bg-orange-500/10 p-2 rounded border border-orange-500/20 text-orange-400"><span className="font-medium">{adv.motivo}</span><span>{adv.data !== "-" ? new Date(adv.data).toLocaleDateString('pt-BR') : ""}</span></div>))}</div>
                    ) : (<span className="text-xs text-slate-500 italic">Nenhuma advertência.</span>)}
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2"><HeartPulse className="w-4 h-4 text-rose-400"/> Saúde Ocupacional</h3>
                <div className="bg-[#1A1F2B] rounded-xl border border-white/5 p-4">
                  <div className="flex justify-between items-end mb-4 border-b border-white/5 pb-3"><span className="text-sm text-slate-300 font-medium">Total de Atestados</span><span className="text-2xl font-bold text-white">{perfilInfo?.historico_atestados?.length || 0}</span></div>
                  <span className="text-xs text-slate-500 font-bold uppercase block mb-2">Histórico (CIDs)</span>
                  {perfilInfo?.historico_atestados?.length > 0 ? (
                    <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar pr-1">{perfilInfo.historico_atestados.map((atst: any, i: number) => (<div key={i} className="text-xs bg-[#232936] p-2.5 rounded-lg border border-white/5 flex flex-col gap-1"><div className="flex justify-between items-center"><span className="font-bold text-emerald-400 line-clamp-1">{atst.motivo}</span><span className="text-slate-500 min-w-[65px] text-right">{atst.data !== "-" ? new Date(atst.data).toLocaleDateString('pt-BR') : ""}</span></div></div>))}</div>
                  ) : (<span className="text-xs text-slate-500 italic block text-center py-2">Sem atestados registrados.</span>)}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MENU LATERAL */}
      {!modoImpressao && (
        <aside className="w-64 bg-[#0B0F19] border-r border-white/5 flex flex-col hide-on-print z-10">
          <div className="p-6 flex items-center gap-3 border-b border-white/5">
            <Activity className="text-blue-500 w-8 h-8" />
            <span className="text-white font-bold text-xl tracking-wide">Folha Analytics</span>
          </div>
          <nav className="flex-1 p-4 space-y-2">
            <button onClick={() => setMenuAtivo("visao_geral")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all text-sm ${menuAtivo === 'visao_geral' ? 'bg-[#1A1F2B] text-white border border-white/5' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><LayoutDashboard className="w-4 h-4" /> Visão Geral</button>
            <button onClick={() => setMenuAtivo("comportamento")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all text-sm ${menuAtivo === 'comportamento' ? 'bg-[#1A1F2B] text-white border border-white/5' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><UsersRound className="w-4 h-4" /> Comportamento e Saúde</button>
            <button onClick={() => setMenuAtivo("financeiro")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all text-sm ${menuAtivo === 'financeiro' ? 'bg-[#1A1F2B] text-white border border-white/5' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><Wallet className="w-4 h-4" /> Financeiro e Passivos</button>
            <button onClick={() => setMenuAtivo("armarios")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all text-sm ${menuAtivo === 'armarios' ? 'bg-[#1A1F2B] text-white border border-white/5' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><Package className="w-4 h-4" /> Gestão de Armários</button>
            <button onClick={() => setMenuAtivo("desempenho")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all text-sm ${menuAtivo === 'desempenho' ? 'bg-[#1A1F2B] text-white border border-white/5' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><Star className="w-4 h-4" /> Desempenho</button>
            
            <div className="pt-4 mt-4 border-t border-white/5">
              <span className="px-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2 block">Motor Inteligente</span>
              <button onClick={() => setMenuAtivo("folha")} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all text-sm ${menuAtivo === 'folha' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}><UploadCloud className="w-4 h-4" /> Automação de Ponto</button>
            </div>
          </nav>
          <div className="p-4 border-t border-white/5">
            <button onClick={handleLogout} className="w-full flex items-center justify-center gap-2 px-4 py-2 hover:bg-red-500/10 text-slate-400 hover:text-red-400 rounded-lg transition-colors text-sm font-medium"><Lock className="w-4 h-4" /> Sair</button>
          </div>
        </aside>
      )}

      <main className={`flex-1 overflow-y-auto ${modoImpressao ? 'p-0' : 'p-8'} ${mainBg}`}>
        
        {!modoImpressao && (
          <header className="flex justify-between items-center mb-8">
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              {menuAtivo === "visao_geral" && `Visão Geral`}
              {menuAtivo === "comportamento" && `Comportamento e Saúde`}
              {menuAtivo === "financeiro" && `Indicadores Financeiros`}
              {menuAtivo === "armarios" && `Controle Físico de Armários`}
              {menuAtivo === "desempenho" && `Performance da Equipe`}
              {menuAtivo === "folha" && `Motor de Automação de Ponto`}
            </h1>
            
            <div className="flex items-center gap-4">
              <button onClick={forcarSincronizacao} disabled={sincronizando} className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors border border-white/5 shadow-sm ${sincronizando ? 'bg-indigo-500/20 text-indigo-400 cursor-wait' : 'bg-[#1A1F2B] text-slate-300 hover:text-white hover:bg-[#232936]'}`}>
                <RefreshCw className={`w-4 h-4 ${sincronizando ? 'animate-spin' : ''}`} /> {sincronizando ? 'Sincronizando Notion...' : 'Atualizar Banco'}
              </button>

              <div className="flex items-center gap-2 bg-[#1A1F2B] border border-white/5 rounded-lg p-1 mr-2 shadow-sm">
                <Briefcase className="w-4 h-4 text-slate-400 ml-2" />
                <select value={setorSelecionado} onChange={(e) => setSetorSelecionado(e.target.value)} className="bg-transparent text-slate-200 text-sm py-1.5 pl-2 pr-6 outline-none cursor-pointer hover:text-white appearance-none" style={{backgroundImage: 'none'}}>
                  <option value="Todos" className="bg-[#1A1F2B] text-white">Todos os Setores</option>
                  {kpis.setoresDisponiveis?.map((setor: string, index: number) => (
                    <option key={index} value={setor} className="bg-[#1A1F2B] text-white">{setor}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2 bg-[#1A1F2B] border border-white/5 rounded-lg p-1 shadow-sm">
                <Calendar className="w-4 h-4 text-slate-400 ml-2" />
                <select value={mesSelecionado} onChange={(e) => setMesSelecionado(Number(e.target.value))} className="bg-transparent text-slate-200 text-sm py-1.5 pl-2 pr-6 outline-none cursor-pointer hover:text-white appearance-none" style={{backgroundImage: 'none'}}>
                  {NOME_MESES.map((nome, index) => (<option key={index} value={index + 1} className="bg-[#1A1F2B] text-white">{nome}</option>))}
                </select>
                <div className="w-px h-4 bg-white/10"></div>
                <select value={anoSelecionado} onChange={(e) => setAnoSelecionado(Number(e.target.value))} className="bg-transparent text-slate-200 text-sm py-1.5 pl-2 pr-6 outline-none cursor-pointer hover:text-white appearance-none" style={{backgroundImage: 'none'}}>
                  {Array.from({length: Math.max(1, new Date().getFullYear() - 2023)}, (_, i) => 2024 + i).map(ano => <option key={ano} value={ano} className="bg-[#1A1F2B] text-white">{ano}</option>)}
                </select>
              </div>
              <button onClick={exportarPDF} disabled={gerandoPdf || menuAtivo === 'folha' || menuAtivo === 'armarios'} className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm border border-white/5 ${gerandoPdf || menuAtivo === 'folha' || menuAtivo === 'armarios' ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 text-white border-none cursor-pointer'}`}>
                <Download className="w-4 h-4" /> {gerandoPdf ? "Gerando PDF..." : "Gerar Relatório A4"}
              </button>
            </div>
          </header>
        )}

        <div className="space-y-2 mb-4" aria-live="polite">
          <p className="text-xs text-slate-400">{syncStatus?.ultima_atualizacao ? `Última atualização: ${new Date(syncStatus.ultima_atualizacao).toLocaleString('pt-BR')}` : 'Nenhuma sincronização disponível.'}{sincronizando ? ' · Atualização em andamento…' : ''}</p>
          {syncStatus?.ultima_atualizacao && Date.now()-new Date(syncStatus.ultima_atualizacao).getTime()>86400000 && <p className="text-amber-300 text-sm">Os dados têm mais de 24 horas. Atualize antes de fechar a competência.</p>}
          {erroDados && <div role="alert" className="p-3 rounded bg-red-950 text-red-200">{erroDados} <button onClick={carregarDadosDashboard} className="underline">Tentar novamente</button></div>}
          {syncStatus?.erro && <p role="alert" className="p-3 rounded bg-amber-950 text-amber-200">{syncStatus.erro}</p>}
          {syncStatus && !syncStatus.tem_dados && <p className="p-3 rounded bg-amber-950 text-amber-200">Sem dados sincronizados. Use “Atualizar Banco” para carregar as bases.</p>}
          {kpis.avisos.length>0 && <details className="p-3 rounded bg-slate-800 text-slate-200 text-sm"><summary className="cursor-pointer">Observações sobre os dados ({kpis.avisos.length})</summary><ul className="list-disc ml-5 mt-2 space-y-1">{kpis.avisos.map(a=><li key={a}>{a}</li>)}</ul></details>}
        </div>
        {indicadorAberto && <IndicadorDetalhes titulo={{funcionarios:'Colaboradores no período',admissoes:'Admissões',desligamentos:'Desligamentos'}[indicadorAberto]} registros={kpis.detalhes[indicadorAberto] || []} fechar={()=>setIndicadorAberto(null)} />}
        {menuAtivo === 'folha' && <FolhaVersoes mes={mesSelecionado} ano={anoSelecionado} atualizacao={mensagemFolha} />}

        <div id="area-relatorio" className={`relative ${erroDados || (syncStatus && !syncStatus.tem_dados) ? "hidden" : ""} ${modoImpressao ? "w-[1200px] mx-auto p-4 space-y-8 bg-slate-50" : "p-2 rounded-lg"}`}>
          
          {carregandoDados && !modoImpressao && (
            <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#0E1218]/80 backdrop-blur-sm rounded-lg">
              <div className="flex flex-col items-center gap-4 bg-[#1A1F2B] p-8 rounded-xl border border-white/10 shadow-2xl">
                <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
                <div className="text-center">
                  <p className="text-white font-bold tracking-wide">Carregando Banco de Dados</p>
                  <p className="text-slate-400 text-xs mt-1">Conectando ao Cache Local (SQLite)...</p>
                </div>
              </div>
            </div>
          )}

          {(menuAtivo === "visao_geral" || modoImpressao) && (
            <>
              {/* ÁREA CAPTURADA PELO PDF */}
              <div id="print-visao" className={modoImpressao ? `p-8 rounded-xl bg-white border border-slate-200 shadow-sm` : ""}>
                <div className={`mb-6 border-b pb-4 ${modoImpressao ? 'border-slate-200' : 'border-white/5'}`}>
                  <h2 className={`text-2xl font-bold ${textColor} tracking-tight uppercase`}>1. Sumário Executivo {setorSelecionado !== "Todos" && <span className="text-blue-500">- {setorSelecionado}</span>}</h2>
                  <p className={`${textMuted} text-sm`}>Gerado em: {new Date().toLocaleDateString('pt-BR')} | Competência: {kpis.periodo_fiscal}</p>
                </div>

                <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-blue-500/10 text-blue-500 rounded-lg"><Users className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Quadro no período</p><h3 className={`text-2xl font-bold ${textColor}`}><button type="button" className="underline decoration-dotted underline-offset-4 hover:text-blue-400" onClick={() => setIndicadorAberto("funcionarios")} aria-label="Conferir colaboradores no período">{kpis.funcionarios}</button></h3><p className={`text-xs ${textMuted}`}>{kpis.comparacao.funcionarios > 0 ? "+" : ""}{kpis.comparacao.funcionarios ?? "—"} vs. competência anterior</p></div></div>
                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-lg"><UserPlus className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Admissões</p><h3 className={`text-2xl font-bold ${textColor}`}><button type="button" className="underline decoration-dotted underline-offset-4 hover:text-blue-400" onClick={() => setIndicadorAberto("admissoes")} aria-label="Conferir admissões">{kpis.admissoes}</button></h3><p className={`text-xs ${textMuted}`}>{kpis.comparacao.admissoes > 0 ? "+" : ""}{kpis.comparacao.admissoes ?? "—"} vs. competência anterior</p><p className={`text-xs ${textMuted}`}>Período: 25 a 24</p></div></div>
                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-rose-500/10 text-rose-500 rounded-lg"><UserMinus className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Desligamentos</p><h3 className={`text-2xl font-bold ${textColor}`}><button type="button" className="underline decoration-dotted underline-offset-4 hover:text-blue-400" onClick={() => setIndicadorAberto("desligamentos")} aria-label="Conferir desligamentos">{kpis.desligamentos}</button></h3><p className={`text-xs ${textMuted}`}>{kpis.comparacao.desligamentos > 0 ? "+" : ""}{kpis.comparacao.desligamentos ?? "—"} vs. competência anterior</p></div></div>
                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-purple-500/10 text-purple-500 rounded-lg"><Activity className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Turnover</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.turnover}</h3><p className={`text-xs ${textMuted}`} title={kpis.base_turnover.formula}>Saídas ÷ quadro no fim do período</p></div></div>
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4 mb-8">
                  <div className={`${cardBg} p-6 rounded-xl`}>
                    <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><TrendingDown className="w-4 h-4 text-purple-500" /> Evolução do Turnover</h3>
                    <div className={modoImpressao ? "h-[300px]" : "h-64"}>
                      {kpis.graficoTurnover.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={kpis.graficoTurnover} margin={{ top: 25, right: 30, left: -20, bottom: 15 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartGrid} />
                            <XAxis dataKey="mes" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} />
                            <YAxis axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} tickFormatter={(value) => `${value}%`} />
                            <Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} itemStyle={{color: tooltipColor}} />
                            <Line isAnimationActive={!modoImpressao} type="monotone" dataKey="turnover" name="Turnover %" stroke="#818CF8" strokeWidth={3} dot={{r: 4, fill: '#818CF8', strokeWidth: 2, stroke: modoImpressao ? '#fff' : '#1A1F2B'}} activeDot={{r: 6}}>
                              <LabelList dataKey="turnover" position="top" fill={chartText} fontSize={11} formatter={(v:any) => `${v}%`} />
                            </Line>
                          </LineChart>
                        </ResponsiveContainer>
                      ) : (<div className="flex h-full items-center justify-center text-slate-500 text-sm italic">Sem dados de turnover.</div>)}
                    </div>
                  </div>
                  <div className={`${cardBg} p-6 rounded-xl`}>
                    <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><UsersRound className="w-4 h-4 text-emerald-500" /> Headcount por Setor</h3>
                    <div className={modoImpressao ? "h-[300px]" : "h-64"}>
                      {kpis.graficoHeadcount.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={kpis.graficoHeadcount} layout="vertical" margin={{ top: 5, right: 40, left: 10, bottom: 15 }}>
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={chartGrid} />
                            <XAxis type="number" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} />
                            <YAxis type="category" dataKey="setor" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 11}} width={100} />
                            <Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} cursor={{fill: chartGrid}} />
                            <Bar isAnimationActive={!modoImpressao} dataKey="quantidade" name="Colaboradores" fill="#34D399" radius={[0, 4, 4, 0]} barSize={20}>
                              <LabelList dataKey="quantidade" position="right" fill={chartText} fontSize={12} fontWeight="bold" />
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (<div className="flex h-full items-center justify-center text-slate-500 text-sm italic">Sem dados de headcount.</div>)}
                    </div>
                  </div>
                  <div className={`${cardBg} p-6 rounded-xl`}>
                    <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><PieChartIcon className="w-4 h-4 text-blue-500" /> Motivos de Desligamento</h3>
                    <div className={modoImpressao ? "h-[300px]" : "h-64 flex justify-center"}>
                      {kpis.graficoMotivos.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart margin={{ bottom: 15 }}>
                            <Pie isAnimationActive={!modoImpressao} data={kpis.graficoMotivos} innerRadius={50} outerRadius={85} paddingAngle={5} dataKey="value" stroke="none" label={({name, value}) => `${(name ?? "Não informado").substring(0,10)}... (${value})`} labelLine={true}>
                              {kpis.graficoMotivos.map((_, index) => (<Cell key={`cell-${index}`} fill={CORES_DONUT[index % CORES_DONUT.length]} />))}
                            </Pie>
                            <Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} itemStyle={{color: tooltipColor}} />
                            <Legend iconType="circle" wrapperStyle={{fontSize: '11px', color: chartText}} />
                          </PieChart>
                        </ResponsiveContainer>
                      ) : (<div className="flex h-full items-center justify-center text-slate-500 text-sm italic">Sem dados de desligamentos.</div>)}
                    </div>
                  </div>
                  <div className={`${cardBg} p-6 rounded-xl`}>
                    <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Activity className="w-4 h-4 text-rose-500" /> Absenteísmo por Setor</h3>
                    <div className={modoImpressao ? "h-[300px]" : "h-64"}>
                      {kpis.graficoSetores.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={kpis.graficoSetores} margin={{ top: 25, right: 20, left: -20, bottom: 25 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartGrid} />
                            <XAxis dataKey="setor" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 10}} interval={0} angle={-30} textAnchor="end" height={60} />
                            <YAxis axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} />
                            <Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} cursor={{fill: chartGrid}} />
                            <Legend iconType="circle" wrapperStyle={{fontSize: '12px', paddingTop: '10px', color: chartText}} />
                            <Bar isAnimationActive={!modoImpressao} dataKey="faltas" name="Faltas" fill="#F43F5E" radius={[4, 4, 0, 0]}>
                              <LabelList dataKey="faltas" position="top" fill={chartText} fontSize={11} />
                            </Bar>
                            <Bar isAnimationActive={!modoImpressao} dataKey="atestados" name="Atestados" fill="#FBBF24" radius={[4, 4, 0, 0]}>
                              <LabelList dataKey="atestados" position="top" fill={chartText} fontSize={11} />
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (<div className="flex h-full items-center justify-center text-slate-500 text-sm italic">Sem dados de absenteísmo.</div>)}
                    </div>
                  </div>
                </div>
              </div>

              {/* TELA DE ALERTAS SOMENTE APARECE FORA DA IMPRESSÃO */}
              {!modoImpressao && (
                <div className={`border-t border-white/5 pt-8 mt-4`}>
                  <h2 className={`text-xl font-bold ${textColor} tracking-tight mb-6 flex items-center gap-3`}>Alertas Operacionais & Clima</h2>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    
                    <div className={`${cardBg} p-6 rounded-xl flex flex-col h-full`}>
                      <div className="flex justify-between items-center mb-6">
                        <h3 className={`text-sm font-bold ${titleColor} flex items-center gap-2 uppercase tracking-wider`}><Gift className="w-4 h-4 text-amber-500" /> Aniversariantes</h3>
                        <div className="flex gap-1 bg-black/20 p-1 rounded-lg border border-white/5">
                          {['Tds', 'S1', 'S2', 'S3', 'S4'].map((label, i) => (
                            <button key={i} onClick={() => setFiltroSemana(i)} className={`text-[10px] font-bold px-2 py-1 rounded transition-colors ${filtroSemana === i ? 'bg-amber-500/20 text-amber-400' : 'text-slate-500 hover:text-slate-300'}`}>{label}</button>
                          ))}
                        </div>
                      </div>
                      <div className="space-y-3 flex-1 pr-2 overflow-y-auto max-h-64 custom-scrollbar">
                        {aniversariosFiltrados.length > 0 ? (
                          aniversariosFiltrados.map((pessoa: any, idx: number) => (
                            <div key={idx} className={`flex justify-between items-center ${itemBg} p-3 rounded-lg border`}>
                              <span className={`text-sm font-medium ${textColor} cursor-pointer hover:text-blue-400 hover:underline transition-all`} onClick={() => setModal360(pessoa.nome)}>{pessoa.nome}</span>
                              <span className={`text-amber-600 text-xs font-bold px-2 py-1 bg-amber-400/10 text-amber-400 rounded-md`}>Dia {pessoa.dia}</span>
                            </div>
                          ))
                        ) : (<p className="text-sm text-slate-400 italic p-3 bg-[#232936]/50 rounded-lg border border-dashed text-center mt-4">Nenhum aniversariante.</p>)}
                      </div>
                    </div>

                    <div className={`${cardBg} p-6 rounded-xl flex flex-col h-full`}>
                      <div className="flex justify-between items-center mb-6 relative z-10">
                        <h3 className={`text-sm font-bold ${titleColor} flex items-center gap-2 uppercase tracking-wider`}><BellRing className="w-4 h-4 text-rose-500" /> Experiência</h3>
                        <div className="flex gap-1 bg-black/20 p-1 rounded-lg border border-white/5">
                          {['45 Dias', '90 Dias'].map((label) => (
                            <button key={label} onClick={() => setFiltroContrato(label)} className={`text-[10px] font-bold px-2 py-1 rounded transition-colors ${filtroContrato === label ? 'bg-rose-500/20 text-rose-400' : 'text-slate-500 hover:text-slate-300'}`}>{label}</button>
                          ))}
                        </div>
                      </div>
                      <div className="space-y-3 relative z-10 flex-1 pr-2 overflow-y-auto max-h-64 custom-scrollbar">
                        {contratosFiltrados.length > 0 ? (
                          contratosFiltrados.map((pessoa: any, idx: number) => {
                            const tagUrgencia = verificarUrgencia(pessoa.dia);
                            const isUrgente = tagUrgencia !== null;
                            return (
                              <div key={idx} className={`flex justify-between items-center p-3 rounded-lg border ${isUrgente ? 'bg-red-500/10 border-red-500/30' : `${itemBg} border-l-2 border-l-rose-500`}`}>
                                <div className="flex flex-col">
                                  <span className={`text-sm font-medium ${isUrgente ? 'text-red-500' : textColor} cursor-pointer hover:text-blue-400 hover:underline transition-all`} onClick={() => setModal360(pessoa.nome)}>{pessoa.nome}</span>
                                  {isUrgente && <span className="text-[10px] text-red-500 font-bold mt-0.5 flex items-center gap-1"><AlertTriangle className="w-3 h-3"/> {tagUrgencia}</span>}
                                </div>
                                <span className={`${isUrgente ? 'text-red-400 bg-red-400/10' : 'text-rose-400 bg-rose-400/10'} text-xs font-bold px-2 py-1 rounded-md`}>Dia {pessoa.dia}</span>
                              </div>
                            )
                          })
                        ) : (<p className="text-sm text-slate-400 italic p-3 bg-[#232936]/50 rounded-lg border border-dashed text-center mt-4">Nenhum contrato vencendo.</p>)}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {(menuAtivo === "comportamento" || modoImpressao) && (
            <>
              {/* ÁREA CAPTURADA PELO PDF */}
              <div id="print-comportamento" className={modoImpressao ? `p-8 rounded-xl bg-white border border-slate-200 shadow-sm` : ""}>
                {modoImpressao && (
                  <div className="mb-6 border-b pb-4 border-slate-200">
                    <h2 className={`text-2xl font-bold ${textColor} tracking-tight uppercase`}>2. Saúde Ocupacional & Comportamento {setorSelecionado !== "Todos" && <span className="text-emerald-500">- {setorSelecionado}</span>}</h2>
                    <p className={`${textMuted} text-sm`}>Gerado em: {new Date().toLocaleDateString('pt-BR')} | Competência: {kpis.periodo_fiscal}</p>
                  </div>
                )}

                <section className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-amber-500/10 text-amber-500 rounded-lg"><Stethoscope className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Atestados</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.atestados}</h3></div></div>
                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-orange-500/10 text-orange-500 rounded-lg"><AlertOctagon className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Advertências</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.advertencias}</h3></div></div>
                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-rose-500/10 text-rose-500 rounded-lg"><Clock className="w-6 h-6" /></div><div className="flex-1"><p className={`text-xs ${textMuted} font-bold uppercase mb-1`}>Frequência</p><div className="flex items-center gap-6"><div><span className={`text-2xl font-bold ${textColor}`}>{kpis.faltas}</span><span className={`text-[10px] ${textMuted} ml-1 font-bold uppercase`}>Faltas</span></div><div className={`w-px h-8 ${modoImpressao ? 'bg-slate-200' : 'bg-white/10'}`}></div><div><span className={`text-2xl font-bold ${textColor}`}>{kpis.atrasos}</span><span className={`text-[10px] ${textMuted} ml-1 font-bold uppercase`}>Atrasos</span></div></div></div></div>
                  <div className={`${cardBg} border-red-200 p-5 rounded-xl flex items-center gap-4`}><div className="p-3 bg-red-500/10 text-red-500 rounded-lg z-10"><DollarSign className="w-6 h-6" /></div><div className="z-10"><p className="text-xs text-red-500 font-bold uppercase mb-1">Impacto Financeiro</p><h3 className={`text-2xl font-bold ${textColor}`}>{formatarMoeda(kpis.custo_absenteismo)}</h3></div></div>
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                  <div className={`${cardBg} p-6 rounded-xl`}>
                    <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Stethoscope className="w-4 h-4 text-emerald-500" /> Médicos Emissores (Top 7)</h3>
                    <div className={modoImpressao ? "h-[300px]" : "h-64"}>
                      {kpis.rankingMedicos.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={kpis.rankingMedicos} layout="vertical" margin={{ top: 5, right: 40, left: 10, bottom: 15 }}>
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={chartGrid} />
                            <XAxis type="number" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} />
                            <YAxis type="category" dataKey="nome" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 11}} width={140} />
                            <Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} cursor={{fill: chartGrid}} />
                            <Bar isAnimationActive={!modoImpressao} dataKey="quantidade" name="Atestados" fill="#10B981" radius={[0, 4, 4, 0]} barSize={16}>
                              <LabelList dataKey="quantidade" position="right" fill={chartText} fontSize={12} fontWeight="bold" />
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (<div className="flex h-full items-center justify-center text-slate-500 text-sm italic">Sem dados de médicos.</div>)}
                    </div>
                  </div>
                  <div className={`${cardBg} p-6 rounded-xl`}>
                    <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Activity className="w-4 h-4 text-rose-500" /> CIDs Mais Frequentes (Top 10)</h3>
                    <div className={modoImpressao ? "h-[300px]" : "h-64"}>
                      {kpis.rankingCids.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={kpis.rankingCids} layout="vertical" margin={{ top: 5, right: 40, left: 10, bottom: 15 }}>
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={chartGrid} />
                            <XAxis type="number" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 12}} />
                            <YAxis type="category" dataKey="nome" axisLine={false} tickLine={false} tick={{fill: chartText, fontSize: 11}} width={220} />
                            <Tooltip contentStyle={{backgroundColor: tooltipBg, borderColor: chartGrid, color: tooltipColor, borderRadius: '8px'}} cursor={{fill: chartGrid}} />
                            <Bar isAnimationActive={!modoImpressao} dataKey="quantidade" name="Ocorrências" fill="#F43F5E" radius={[0, 4, 4, 0]} barSize={16}>
                              <LabelList dataKey="quantidade" position="right" fill={chartText} fontSize={12} fontWeight="bold" />
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (<div className="flex h-full items-center justify-center text-slate-500 text-sm italic">Sem dados de CIDs.</div>)}
                    </div>
                  </div>
                </div>
              </div>

              {/* TELA DE TOP 5 LATERAL SOMENTE APARECE FORA DA IMPRESSÃO */}
              {!modoImpressao && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                  <div className={`${cardBg} p-6 rounded-xl flex flex-col`}>
                    <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><TrendingDown className="w-4 h-4 text-rose-500" /> Ofensores de Faltas (Top 5)</h3>
                    <div className="space-y-3 flex-1 pr-2 overflow-y-auto max-h-64 custom-scrollbar">
                      {kpis.rankingFaltas?.slice(0, 5).map((pessoa: any, idx: number) => (
                        <div key={idx} className={`flex justify-between items-center ${itemBg} p-3 rounded-lg border`}>
                          <div className="flex items-center gap-3">
                            <span className="w-6 h-6 flex items-center justify-center rounded-full bg-slate-800 text-xs font-bold text-slate-400">{idx + 1}º</span>
                            <span className="text-sm font-medium text-white cursor-pointer hover:text-blue-400 hover:underline transition-all" onClick={() => setModal360(pessoa.nome)}>{pessoa.nome}</span>
                          </div>
                          <span className="text-rose-400 bg-rose-400/10 text-xs font-bold px-2 py-1 rounded-md">{pessoa.faltas} dias</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className={`${cardBg} p-6 rounded-xl flex flex-col`}>
                    <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Stethoscope className="w-4 h-4 text-emerald-500" /> Volume de Atestados (Top 5)</h3>
                    <div className="space-y-3 flex-1 pr-2 overflow-y-auto max-h-64 custom-scrollbar">
                      {kpis.rankingAtestados?.slice(0, 5).map((pessoa: any, idx: number) => (
                        <div key={idx} className={`flex justify-between items-center ${itemBg} p-3 rounded-lg border`}>
                          <div className="flex items-center gap-3">
                            <span className="w-6 h-6 flex items-center justify-center rounded-full bg-slate-800 text-xs font-bold text-slate-400">{idx + 1}º</span>
                            <span className="text-sm font-medium text-white cursor-pointer hover:text-blue-400 hover:underline transition-all" onClick={() => setModal360(pessoa.nome)}>{pessoa.nome}</span>
                          </div>
                          <span className="text-emerald-400 bg-emerald-400/10 text-xs font-bold px-2 py-1 rounded-md">{pessoa.atestados} atestados</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {menuAtivo === "financeiro" && !modoImpressao && (
            <>
              {/* ÁREA CAPTURADA PELO PDF */}
              <div id="print-financeiro" className={modoImpressao ? `p-8 rounded-xl bg-white border border-slate-200 shadow-sm` : ""}>
                {modoImpressao && (
                  <div className="mb-6 border-b pb-4 border-slate-200">
                    <h2 className={`text-2xl font-bold ${textColor} tracking-tight uppercase`}>3. Indicadores Financeiros e Passivos {setorSelecionado !== "Todos" && <span className="text-red-500">- {setorSelecionado}</span>}</h2>
                    <p className={`${textMuted} text-sm`}>Gerado em: {new Date().toLocaleDateString('pt-BR')} | Competência: {kpis.periodo_fiscal}</p>
                  </div>
                )}

                <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4 border-red-500/30`}>
                    <div className="p-3 bg-red-500/10 text-red-500 rounded-lg"><DollarSign className="w-6 h-6" /></div>
                    <div><p className={`text-xs ${textMuted} font-bold uppercase mb-1`}>Custo de Absenteísmo</p><h3 className={`text-2xl font-bold text-red-400`}>{formatarMoeda(kpis.custo_absenteismo)}</h3></div>
                  </div>
                  
                  {/* CARD DE HORAS EXTRAS INTERATIVO COM UPLOAD */}
                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4 relative group overflow-hidden cursor-pointer border border-transparent hover:border-amber-500/30 transition-all`}>
                    <input type="file" accept=".xls,.xlsx" onChange={handleAtualizarDashboardHoras} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" title="Clique para anexar arquivo de ponto" />
                    <div className={`p-3 rounded-lg ${processandoDashboard ? 'bg-slate-700 text-slate-400 animate-pulse' : 'bg-amber-500/10 text-amber-500 group-hover:scale-110 transition-transform'}`}>
                      {processandoDashboard ? <Loader2 className="w-6 h-6 animate-spin" /> : <Clock className="w-6 h-6" />}
                    </div>
                    <div>
                      <p className={`text-xs ${textMuted} font-bold uppercase mb-1 flex items-center gap-2`}>
                        Horas Extras Realizadas
                        <span className="opacity-0 group-hover:opacity-100 text-[9px] bg-amber-500/20 text-amber-500 px-1.5 rounded transition-opacity">Upload</span>
                      </p>
                      <h3 className={`text-2xl font-bold ${textColor}`}>
                        {dadosHorasExtras ? dadosHorasExtras.total_horas_empresa : '0'} 
                        <span className="text-sm text-slate-500 ml-1">horas</span>
                      </h3>
                    </div>
                  </div>

                  <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4`}>
                    <div className="p-3 bg-rose-500/10 text-rose-500 rounded-lg"><CalendarRange className="w-6 h-6" /></div>
                    <div><p className={`text-xs ${textMuted} font-bold uppercase mb-1`}>Férias em Risco de Dobra</p><h3 className={`text-2xl font-bold ${textColor}`}>{kpis.alertasFerias?.length || 0} <span className="text-sm text-slate-500">colaboradores</span></h3></div>
                  </div>
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                  {/* TELA DE FÉRIAS */}
                  {!modoImpressao && (
                    <div className={`${cardBg} p-6 rounded-xl flex flex-col`}>
                      <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Flame className="w-4 h-4 text-rose-500" /> Alerta de Passivo (Férias Vencendo)</h3>
                      <div className="space-y-3 flex-1 pr-2 overflow-y-auto max-h-[320px] custom-scrollbar">
                        {kpis.alertasFerias?.length > 0 ? (
                          kpis.alertasFerias.map((pessoa: any, idx: number) => {
                            const critico = pessoa.dias_restantes <= 30; 
                            return (
                              <div key={idx} className={`flex justify-between items-center p-3 rounded-lg border ${critico ? 'bg-red-500/10 border-red-500/30' : itemBg}`}>
                                <div className="flex flex-col">
                                  <span className={`text-sm font-medium ${critico ? 'text-red-400' : textColor} cursor-pointer hover:text-blue-400 hover:underline transition-all`} onClick={() => setModal360(pessoa.nome)}>{pessoa.nome}</span>
                                  <span className="text-xs text-slate-500 mt-0.5">{pessoa.setor}</span>
                                </div>
                                <span className={`${critico ? 'text-red-500 font-bold flex items-center gap-1' : 'text-orange-400 font-medium'} text-xs px-2 py-1 bg-black/20 rounded-md`}>{critico && <AlertTriangle className="w-3 h-3" />}Dobra em {pessoa.dias_restantes} dias</span>
                              </div>
                            )
                          })
                        ) : (<p className="text-sm text-slate-400 italic p-4 bg-[#232936]/50 rounded-lg border border-dashed text-center mt-4">Nenhum colaborador com risco de férias em dobro nos próximos 4 meses.</p>)}
                      </div>
                    </div>
                  )}

                  {/* GRÁFICO DINÂMICO DE HORAS EXTRAS EM TEMPO REAL */}
                  <div className={`${cardBg} p-6 rounded-xl ${modoImpressao ? 'col-span-2' : 'flex flex-col'}`}>
                    <div className="flex justify-between items-center mb-6">
                      <h3 className={`text-sm font-bold ${titleColor} flex items-center gap-2 uppercase tracking-wider`}><Wallet className="w-4 h-4 text-amber-500" /> Volume de Horas Extras (Por Setor)</h3>
                      {arquivoDashboard && <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded font-mono border border-emerald-500/30 line-clamp-1 max-w-[150px]">{arquivoDashboard.name}</span>}
                    </div>
                    
                    <div className={modoImpressao ? "h-[300px]" : "h-[320px] relative overflow-y-auto custom-scrollbar pr-2"}>
                      {processandoDashboard && (
                        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#1A1F2B]/90 rounded-lg">
                          <Loader2 className="w-8 h-8 text-amber-500 animate-spin mb-3" />
                          <p className="text-slate-300 text-sm font-bold">Processando Ponto...</p>
                        </div>
                      )}
                      
                      {dadosHorasExtras && dadosHorasExtras.grafico_setores?.length > 0 ? (
                        <div className="space-y-4 pt-1">
                          {dadosHorasExtras.grafico_setores.map((setor: any, idx: number) => {
                            const maiorValor = dadosHorasExtras.grafico_setores[0].minutos_absolutos;
                            const porcentagem = Math.max(5, (setor.minutos_absolutos / maiorValor) * 100);
                            
                            return (
                              <div key={idx} className="group flex flex-col gap-1.5">
                                <div className="flex justify-between items-end">
                                  <span className="text-sm font-medium text-slate-300">{setor.setor}</span>
                                  <span className="text-xs font-bold text-amber-500">{setor.horas_formatadas}</span>
                                </div>
                                <div className="w-full h-3 bg-[#0E1218] rounded-full overflow-hidden border border-white/5">
                                  <div className="h-full bg-gradient-to-r from-amber-600 to-amber-400 rounded-full transition-all duration-1000 ease-out relative group-hover:brightness-125" style={{ width: `${porcentagem}%` }}></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="flex flex-col h-full items-center justify-center text-slate-500 text-sm italic relative">
                          <p className="mb-2">Nenhum arquivo processado.</p>
                          <p className="text-xs text-slate-600 font-sans px-8 text-center">Clique no card "Horas Extras Realizadas" ali em cima e envie o espelho do SAP de qualquer período.</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {(menuAtivo === "armarios" && !modoImpressao) && (
            <div id="print-armarios" className="p-2 rounded-lg">
              <section className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4 border-l-4 border-l-blue-500`}><div className="p-3 bg-blue-500/10 text-blue-500 rounded-lg"><Package className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Total de Armários</p><h3 className={`text-2xl font-bold ${textColor}`}>{totalArmarios}</h3></div></div>
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4 border-l-4 border-l-emerald-500`}><div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-lg"><Unlock className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Livres</p><h3 className={`text-2xl font-bold ${textColor}`}>{livres}</h3></div></div>
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4 border-l-4 border-l-indigo-500`}><div className="p-3 bg-indigo-500/10 text-indigo-500 rounded-lg"><LockKeyhole className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Ocupados</p><h3 className={`text-2xl font-bold ${textColor}`}>{ocupados}</h3></div></div>
                <div className={`${cardBg} p-5 rounded-xl flex items-center gap-4 border-l-4 border-l-orange-500`}><div className="p-3 bg-orange-500/10 text-orange-500 rounded-lg"><Wrench className="w-6 h-6" /></div><div><p className={`text-xs ${textMuted} font-bold uppercase`}>Manutenção</p><h3 className={`text-2xl font-bold ${textColor}`}>{manutencao}</h3></div></div>
              </section>

              <div className={`${cardBg} p-6 rounded-xl`}>
                <h3 className={`text-sm font-bold ${titleColor} mb-6 flex items-center gap-2 uppercase tracking-wider`}><Package className="w-4 h-4 text-slate-500" /> Mapa de Ocupação {setorSelecionado !== "Todos" && <span className="text-slate-400 capitalize">- Somente {setorSelecionado}</span>}</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                  {armariosReais.length > 0 ? (
                    armariosReais.map((armario:any, index:number) => {
                      let boxStyle = "";
                      let icon = null;
                      if (armario.status === "Livre") { boxStyle = "bg-[#1A1F2B] border-2 border-emerald-500/30 hover:border-emerald-500 transition-colors"; icon = <Unlock className="w-4 h-4 text-emerald-500 mb-1" />; } 
                      else if (armario.status === "Ocupado") { boxStyle = "bg-indigo-500/10 border-2 border-indigo-500/50 hover:border-indigo-400 transition-colors"; icon = <LockKeyhole className="w-4 h-4 text-indigo-500 mb-1" />; } 
                      else if (armario.status === "Manutenção") { boxStyle = "bg-[#1A1F2B] border-2 border-dashed border-orange-500/50 flex-col items-center justify-center text-center opacity-60"; icon = <Wrench className="w-4 h-4 text-orange-500 mb-1" />; }
                      return (
                        <div key={index} className={`relative rounded-xl p-3 flex flex-col justify-between aspect-square cursor-pointer ${boxStyle}`}>
                          <div className="flex justify-between items-start"><span className="text-lg font-black text-white">#{armario.num}</span>{icon}</div>
                          <div className="mt-2">
                            <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded flex w-fit mb-1 ${armario.status === 'Livre' ? 'bg-emerald-500/20 text-emerald-500' : armario.status === 'Ocupado' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-orange-500/20 text-orange-500'}`}>{armario.status}</span>
                            {armario.status === "Ocupado" && armario.dono && (<span className="text-xs font-medium line-clamp-2 leading-tight text-slate-300">{armario.dono}</span>)}
                            {armario.status === "Livre" && (<span className="text-xs text-emerald-500/70 italic">Disponível</span>)}
                          </div>
                        </div>
                      );
                    })
                  ) : (<div className="col-span-full py-8 text-center border border-dashed border-white/10 rounded-lg"><p className="text-slate-400 text-sm">Nenhum armário encontrado no banco de dados.</p></div>)}
                </div>
              </div>
            </div>
          )}

          {/* DESEMPENHO SÓ APARECE FORA DA IMPRESSÃO */}
          {(menuAtivo === "desempenho" && !modoImpressao) && (
            <div className="p-2 rounded-lg">
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

          {/* PÁGINAS DE RANKING DINÂMICO (SÓ APARECEM NA IMPRESSÃO) */}
          {modoImpressao && (
            <>
              <div id="print-ranking-faltas" className="p-8 rounded-xl bg-white border border-slate-200 shadow-sm mt-8">
                <div className="mb-8 border-b pb-4 border-slate-200">
                  <h2 className="text-2xl font-bold text-slate-800 tracking-tight uppercase">
                    Top {setorSelecionado === 'Todos' ? '5' : '10'} Ofensores de Faltas {setorSelecionado !== 'Todos' && <span className="text-rose-500">- {setorSelecionado}</span>}
                  </h2>
                  <p className="text-slate-500 text-sm">Gerado em: {new Date().toLocaleDateString('pt-BR')} | Competência: {kpis.periodo_fiscal}</p>
                </div>
                <div className="space-y-4">
                  {kpis.rankingFaltas?.slice(0, setorSelecionado === 'Todos' ? 5 : 10).map((pessoa: any, idx: number) => (
                    <div key={idx} className="flex justify-between items-center bg-slate-50 p-4 rounded-xl border border-slate-200">
                      <div className="flex items-center gap-4">
                        <span className="w-8 h-8 flex items-center justify-center rounded-full bg-slate-200 text-sm font-bold text-slate-600">{idx + 1}º</span>
                        <span className="text-lg font-bold text-slate-800">{pessoa.nome}</span>
                      </div>
                      <span className="text-rose-700 bg-rose-100 text-sm font-bold px-4 py-2 rounded-lg">{pessoa.faltas} dias ausentes</span>
                    </div>
                  ))}
                  {(!kpis.rankingFaltas || kpis.rankingFaltas.length === 0) && (
                    <p className="text-slate-500 text-center py-8">Nenhuma falta registrada neste período.</p>
                  )}
                </div>
              </div>

              <div id="print-ranking-atestados" className="p-8 rounded-xl bg-white border border-slate-200 shadow-sm mt-8">
                <div className="mb-8 border-b pb-4 border-slate-200">
                  <h2 className="text-2xl font-bold text-slate-800 tracking-tight uppercase">
                    Top {setorSelecionado === 'Todos' ? '5' : '10'} Volume de Atestados {setorSelecionado !== 'Todos' && <span className="text-emerald-500">- {setorSelecionado}</span>}
                  </h2>
                  <p className="text-slate-500 text-sm">Gerado em: {new Date().toLocaleDateString('pt-BR')} | Competência: {kpis.periodo_fiscal}</p>
                </div>
                <div className="space-y-4">
                  {kpis.rankingAtestados?.slice(0, setorSelecionado === 'Todos' ? 5 : 10).map((pessoa: any, idx: number) => (
                    <div key={idx} className="flex justify-between items-center bg-slate-50 p-4 rounded-xl border border-slate-200">
                      <div className="flex items-center gap-4">
                        <span className="w-8 h-8 flex items-center justify-center rounded-full bg-slate-200 text-sm font-bold text-slate-600">{idx + 1}º</span>
                        <span className="text-lg font-bold text-slate-800">{pessoa.nome}</span>
                      </div>
                      <span className="text-emerald-800 bg-emerald-100 text-sm font-bold px-4 py-2 rounded-lg">{pessoa.atestados} atestados</span>
                    </div>
                  ))}
                  {(!kpis.rankingAtestados || kpis.rankingAtestados.length === 0) && (
                    <p className="text-slate-500 text-center py-8">Nenhum atestado registrado neste período.</p>
                  )}
                </div>
              </div>

              <div id="print-ranking-advertencias" className="p-8 rounded-xl bg-white border border-slate-200 shadow-sm mt-8">
                <div className="mb-8 border-b pb-4 border-slate-200">
                  <h2 className="text-2xl font-bold text-slate-800 tracking-tight uppercase">
                    Top {setorSelecionado === 'Todos' ? '5' : '10'} Advertências {setorSelecionado !== 'Todos' && <span className="text-orange-500">- {setorSelecionado}</span>}
                  </h2>
                  <p className="text-slate-500 text-sm">Gerado em: {new Date().toLocaleDateString('pt-BR')} | Competência: {kpis.periodo_fiscal}</p>
                </div>
                <div className="space-y-4">
                  {kpis.rankingAdvertencias?.slice(0, setorSelecionado === 'Todos' ? 5 : 10).map((pessoa: any, idx: number) => (
                    <div key={idx} className="flex justify-between items-center bg-slate-50 p-4 rounded-xl border border-slate-200">
                      <div className="flex items-center gap-4">
                        <span className="w-8 h-8 flex items-center justify-center rounded-full bg-slate-200 text-sm font-bold text-slate-600">{idx + 1}º</span>
                        <span className="text-lg font-bold text-slate-800">{pessoa.nome}</span>
                      </div>
                      <span className="text-orange-800 bg-orange-100 text-sm font-bold px-4 py-2 rounded-lg">{pessoa.advertencias} ocorrências</span>
                    </div>
                  ))}
                  {(!kpis.rankingAdvertencias || kpis.rankingAdvertencias.length === 0) && (
                    <p className="text-slate-500 text-center py-8">Nenhuma advertência registrada neste período.</p>
                  )}
                </div>
              </div>
            </>
          )}

          {/* ========================================================= */}
          {/* NOVA ABA: MOTOR DE AUTOMAÇÃO DE PONTO E RPA (INTERFACE) */}
          {/* ========================================================= */}
          {(menuAtivo === "folha" && !modoImpressao) && (
            <div className="p-2 rounded-lg fade-in">
              <div className={`${cardBg} p-8 rounded-xl border border-white/5`}>
                
                {/* MENU DE OPÇÕES GERAL DA FOLHA */}
                <div className="flex gap-4 mb-8 border-b border-white/10 pb-6 overflow-x-auto custom-scrollbar">
                  <button onClick={() => setModoFolha('calculo')} className={`whitespace-nowrap px-6 py-3 font-bold rounded-lg transition-all flex items-center gap-2 shadow-sm ${modoFolha === 'calculo' ? 'bg-emerald-600 text-white border-emerald-500' : 'bg-[#232936] text-slate-400 border border-white/5 hover:text-white'}`}>
                    <Activity className="w-5 h-5" /> Motor Financeiro (DSR/Faltas)
                  </button>
                  <button onClick={() => setModoFolha('rpa')} className={`whitespace-nowrap px-6 py-3 font-bold rounded-lg transition-all flex items-center gap-2 shadow-sm ${modoFolha === 'rpa' ? 'bg-blue-600 text-white border-blue-500' : 'bg-[#232936] text-slate-400 border border-white/5 hover:text-white'}`}>
                    <Bot className="w-5 h-5" /> Robô RPA (Contabilidade)
                  </button>
                  <button onClick={() => setModoFolha('auditor')} className={`whitespace-nowrap px-6 py-3 font-bold rounded-lg transition-all flex items-center gap-2 shadow-sm ${modoFolha === 'auditor' ? 'bg-red-600 text-white border-red-500' : 'bg-[#232936] text-slate-400 border border-white/5 hover:text-white'}`}>
                    <AlertOctagon className="w-5 h-5" /> Auditoria Contador vs Holerite
                  </button>
                  <button onClick={() => setModoFolha('convocacao')} className={`whitespace-nowrap px-6 py-3 font-bold rounded-lg transition-all flex items-center gap-2 shadow-sm ${modoFolha === 'convocacao' ? 'bg-purple-600 text-white border-purple-500' : 'bg-[#232936] text-slate-400 border border-white/5 hover:text-white'}`}>
                    <CalendarRange className="w-5 h-5" /> Auditoria de Termos Extraordinários
                  </button>
                  <button onClick={() => setModoFolha('vales')} className={`whitespace-nowrap px-6 py-3 font-bold rounded-lg transition-all flex items-center gap-2 shadow-sm ${modoFolha === 'vales' ? 'bg-orange-600 text-white border-orange-500' : 'bg-[#232936] text-slate-400 border border-white/5 hover:text-white'}`}>
                    <ShoppingCart className="w-5 h-5" /> Lançamento de Vales
                  </button>
                  <button onClick={() => setModoFolha('farmacia')} className={`whitespace-nowrap px-6 py-3 font-bold rounded-lg transition-all flex items-center gap-2 shadow-sm ${modoFolha === 'farmacia' ? 'bg-pink-600 text-white border-pink-500' : 'bg-[#232936] text-slate-400 border border-white/5 hover:text-white'}`}>
                    <Pill className="w-5 h-5" /> Convênio Farmácia
                  </button>
                  <button onClick={() => setModoFolha('bonus')} className={`whitespace-nowrap px-6 py-3 font-bold rounded-lg transition-all flex items-center gap-2 shadow-sm ${modoFolha === 'bonus' ? 'bg-amber-600 text-white border-amber-500' : 'bg-[#232936] text-slate-400 border border-white/5 hover:text-white'}`}>
                    <Award className="w-5 h-5" /> Fechamento de Bônus
                  </button>
                  <button onClick={() => setModoFolha('auditor_bonus')} className={`whitespace-nowrap px-6 py-3 font-bold rounded-lg transition-all flex items-center gap-2 shadow-sm ${modoFolha === 'auditor_bonus' ? 'bg-amber-600 text-white border-amber-500' : 'bg-[#232936] text-slate-400 border border-white/5 hover:text-white'}`}>
                    <AlertOctagon className="w-5 h-5" /> Auditoria Ponto vs Bônus
                  </button>
                </div>

                {/* ========================================= */}
                {/* TELA 1: MOTOR FINANCEIRO (ANTIGA)         */}
                {/* ========================================= */}
                {modoFolha === 'calculo' && (
                  <div>
                    {resultadoPonto.length === 0 && !processandoPonto && (
                      <div className="text-center flex flex-col items-center justify-center py-8">
                        <div className="w-16 h-16 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center justify-center mb-6"><UploadCloud className="w-8 h-8" /></div>
                        <h2 className={`text-2xl font-bold ${textColor} mb-2`}>Auditoria de Faltas e Descontos</h2>
                        <p className={`${textMuted} text-sm max-w-md mx-auto mb-8`}>Arraste o arquivo <b>sap_009.xls</b>. O sistema cruzará os nomes com o Banco de Dados do Notion para calcular o desconto exato em R$.</p>
                        <div className="relative w-full max-w-2xl border-2 border-dashed border-slate-600 rounded-xl p-10 hover:border-emerald-500 hover:bg-emerald-500/5 transition-all cursor-pointer group">
                          <input type="file" accept=".xls,.xlsx,.csv" onChange={handleFileUpload} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                          <UploadCloud className="w-10 h-10 text-slate-500 mx-auto mb-4 group-hover:text-emerald-500 transition-colors" />
                          <p className="text-slate-300 font-medium">Clique ou arraste o arquivo do ponto aqui</p>
                          <p className="text-slate-500 text-xs mt-2">Somente extrações originais do SAP.</p>
                        </div>
                        {erroPonto && <div className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm font-medium">{erroPonto}</div>}
                      </div>
                    )}
                    {processandoPonto && (
                      <div className="text-center py-20 flex flex-col items-center">
                        <Loader2 className="w-12 h-12 text-emerald-500 animate-spin mb-4" />
                        <p className="text-white font-bold text-lg">Lendo milhares de linhas e cruzando salários base...</p>
                      </div>
                    )}
                    {resultadoPonto.length > 0 && !processandoPonto && (
                      <div className="fade-in">
                        <div className="flex justify-between items-center mb-8 border-b border-white/10 pb-6">
                          <div>
                            <h2 className="text-2xl font-bold text-white flex items-center gap-3"><CheckCircle2 className="w-6 h-6 text-emerald-500"/> Sucesso! Relatório Processado</h2>
                            <p className="text-slate-400 text-sm mt-1">{resultadoPonto.length} funcionários calculados para {NOME_MESES[mesSelecionado-1]}/{anoSelecionado}.</p>
                          </div>
                          <div className="flex items-center gap-3">
                            {mensagemFolha && <span className="text-sm font-medium text-emerald-400 animate-pulse">{mensagemFolha}</span>}
                            <button onClick={() => setResultadoPonto([])} disabled={salvandoFolha} className="px-4 py-2 bg-[#232936] hover:bg-[#2A3142] text-white text-sm font-medium rounded-lg transition-colors border border-white/5">Cancelar</button>
                            <button onClick={handleSalvarFolha} disabled={salvandoFolha} className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-lg transition-colors shadow-lg flex items-center gap-2">
                              {salvandoFolha ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wallet className="w-4 h-4" />}
                              {salvandoFolha ? 'Gravando no BD...' : 'Efetivar Lançamento'}
                            </button>
                          </div>
                        </div>
                        <div className="overflow-x-auto rounded-xl border border-white/10">
                          <table className="w-full text-left border-collapse">
                            <thead>
                              <tr className="bg-[#232936]">
                                <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-white/10">Colaborador</th>
                                <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-white/10">Setor</th>
                                <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-white/10">Salário Base</th>
                                <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-white/10">Tempo Descontado</th>
                                <th className="p-4 text-xs font-bold text-amber-500 uppercase tracking-wider border-b border-white/10">Faltas (Dias)</th>
                                <th className="p-4 text-xs font-bold text-rose-500 uppercase tracking-wider border-b border-white/10">Impacto (R$)</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 bg-[#1A1F2B]">
                              {resultadoPonto.map((row, idx) => (
                                <tr key={idx} className="hover:bg-white/5 transition-colors">
                                  <td className="p-4"><span className={`text-sm font-medium ${row.salario_base === 0 ? 'text-orange-400' : 'text-white'}`}>{row.nome}</span></td>
                                  <td className="p-4 text-sm text-slate-300">{row.setor}</td>
                                  <td className="p-4 text-sm text-slate-400">{formatarMoeda(row.salario_base)}</td>
                                  <td className="p-4"><span className="px-2.5 py-1 bg-[#232936] text-slate-300 rounded text-xs font-bold font-mono border border-white/5">{row.horas_desconto}</span></td>
                                  <td className="p-4 font-bold text-amber-400">{row.faltas_dias > 0 ? `${row.faltas_dias}d` : '-'}</td>
                                  <td className="p-4 font-bold text-rose-400">{formatarMoeda(row.valor_desconto)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ========================================= */}
                {/* TELA 2: NOVO ROBÔ RPA CONTABILIDADE       */}
                {/* ========================================= */}
                {modoFolha === 'rpa' && (
                  <div className="fade-in py-4">
                    <div className="text-center flex flex-col items-center justify-center mb-10">
                      <div className="w-16 h-16 bg-blue-500/10 text-blue-500 rounded-full flex items-center justify-center mb-6"><Bot className="w-8 h-8" /></div>
                      <h2 className={`text-2xl font-bold ${textColor} mb-2`}>Robô RPA: Fechamento Contábil</h2>
                      <p className={`${textMuted} text-sm max-w-lg mx-auto`}>Anexe o espelho do SAP e a planilha oficial do escritório. O robô vai ler todas as matrículas, preencher as <b>Horas Extras</b> nas colunas amarelas sem estragar as cores e devolver a planilha pronta.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-8">
                      {/* CAIXA 1: SAP */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoSapRpa ? 'border-emerald-500 bg-emerald-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-blue-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoSapRpa(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoSapRpa ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-3" />
                             <span className="text-emerald-400 font-bold text-sm text-center line-clamp-1">{arquivoSapRpa.name}</span>
                             <span className="text-slate-500 text-xs mt-1">Arquivo SAP pronto.</span>
                           </>
                         ) : (
                           <>
                             <UploadCloud className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">1. Arquivo SAP (.xls)</span>
                             <span className="text-slate-500 text-xs mt-1 text-center">Onde estão as horas registradas</span>
                           </>
                         )}
                      </div>

                      {/* CAIXA 2: PLANILHA ESCRITORIO */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoBaseRpa ? 'border-emerald-500 bg-emerald-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-blue-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoBaseRpa(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoBaseRpa ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-3" />
                             <span className="text-emerald-400 font-bold text-sm text-center line-clamp-1">{arquivoBaseRpa.name}</span>
                             <span className="text-slate-500 text-xs mt-1">Planilha Base pronta.</span>
                           </>
                         ) : (
                           <>
                             <Briefcase className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">2. Planilha Base (.xlsx)</span>
                             <span className="text-slate-500 text-xs mt-1 text-center">A planilha oficial que vai pro contador</span>
                           </>
                         )}
                      </div>
                    </div>

                    <div className="flex justify-center">
                      <button onClick={handleGerarRPA} disabled={gerandoRpa || !arquivoSapRpa || !arquivoBaseRpa} className={`px-8 py-4 rounded-xl font-bold text-sm transition-all shadow-lg flex items-center gap-3 ${gerandoRpa ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : (!arquivoSapRpa || !arquivoBaseRpa) ? 'bg-[#232936] text-slate-500 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 text-white hover:shadow-blue-500/20 hover:-translate-y-1'}`}>
                        {gerandoRpa ? <Loader2 className="w-5 h-5 animate-spin" /> : <Bot className="w-5 h-5" />}
                        {gerandoRpa ? 'Robô trabalhando... Aguarde' : 'INICIAR RPA E BAIXAR PLANILHA'}
                      </button>
                    </div>

                  </div>
                )}

                {/* ========================================= */}
                {/* TELA 3: AUDITOR DE FOLHA (MÁXIMA SEGURANÇA)*/}
                {/* ========================================= */}
                {modoFolha === 'auditor' && (
                  <div className="fade-in py-4">
                    <div className="text-center flex flex-col items-center justify-center mb-10">
                      <div className="w-16 h-16 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center mb-6"><AlertOctagon className="w-8 h-8" /></div>
                      <h2 className={`text-2xl font-bold ${textColor} mb-2`}>Auditoria Final: Planilha vs. Holerites</h2>
                      <p className={`${textMuted} text-sm max-w-lg mx-auto`}>Antes de fechar a folha, anexe a <b>Planilha que você enviou</b> e o <b>PDF dos Holerites</b> que o contador retornou. O robô vai cruzar todos os DSRs e Faltas para garantir que nada foi lançado errado.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-8">
                      {/* CAIXA 1: PDF DOS HOLERITES */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoPdfHolerite ? 'border-red-500 bg-red-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-red-500'}`}>
                         <input type="file" accept=".pdf" onChange={(e) => setArquivoPdfHolerite(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoPdfHolerite ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-red-500 mb-3" />
                             <span className="text-red-400 font-bold text-sm text-center line-clamp-1">{arquivoPdfHolerite.name}</span>
                           </>
                         ) : (
                           <>
                             <UploadCloud className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">1. PDF dos Holerites</span>
                           </>
                         )}
                      </div>

                      {/* CAIXA 2: PLANILHA ESCRITORIO */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoBaseRpa ? 'border-red-500 bg-red-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-red-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoBaseRpa(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoBaseRpa ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-red-500 mb-3" />
                             <span className="text-red-400 font-bold text-sm text-center line-clamp-1">{arquivoBaseRpa.name}</span>
                           </>
                         ) : (
                           <>
                             <Briefcase className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">2. Sua Planilha Base (.xlsx)</span>
                           </>
                         )}
                      </div>
                    </div>

                    <div className="flex justify-center mb-10">
                      <button onClick={handleAuditarFolha} disabled={processandoAuditoria || !arquivoPdfHolerite || !arquivoBaseRpa} className={`px-8 py-4 rounded-xl font-bold text-sm transition-all shadow-lg flex items-center gap-3 ${processandoAuditoria ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : (!arquivoPdfHolerite || !arquivoBaseRpa) ? 'bg-[#232936] text-slate-500 cursor-not-allowed' : 'bg-red-600 hover:bg-red-500 text-white hover:shadow-red-500/20 hover:-translate-y-1'}`}>
                        {processandoAuditoria ? <Loader2 className="w-5 h-5 animate-spin" /> : <Activity className="w-5 h-5" />}
                        {processandoAuditoria ? 'Cruzando centenas de dados...' : 'INICIAR AUDITORIA DE FOLHA'}
                      </button>
                    </div>

                    {/* RESULTADO DA AUDITORIA */}
                    {resultadoAuditoria && (
                      <div className="fade-in bg-[#1A1F2B] rounded-xl border border-white/10 p-6">
                        <div className="flex justify-between items-center mb-6">
                          <div>
                            <h3 className="text-lg font-bold text-white">Relatório de Divergências</h3>
                            <p className="text-slate-400 text-sm">Foram lidos {resultadoAuditoria.total_auditados} holerites.</p>
                          </div>
                        </div>
                        
                        {resultadoAuditoria.divergencias.length === 0 ? (
                          <div className="bg-emerald-500/10 border border-emerald-500/30 p-6 rounded-xl text-center">
                            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                            <h4 className="text-emerald-400 font-bold text-lg">Folha 100% Sincronizada!</h4>
                            <p className="text-emerald-500/70 text-sm mt-1">Nenhuma diferença de Faltas ou DSR entre a sua planilha e os holerites gerados pelo contador.</p>
                          </div>
                        ) : (
                          <div className="overflow-x-auto rounded-xl border border-white/10">
                            <table className="w-full text-left border-collapse">
                              <thead>
                                <tr className="bg-[#232936]">
                                  <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-white/10">Colaborador</th>
                                  <th className="p-4 text-xs font-bold text-blue-400 uppercase tracking-wider border-b border-white/10">Faltas (Sua Planilha)</th>
                                  <th className="p-4 text-xs font-bold text-blue-400 uppercase tracking-wider border-b border-white/10">DSR (Sua Planilha)</th>
                                  <th className="p-4 text-xs font-bold text-orange-400 uppercase tracking-wider border-b border-white/10">Faltas (Holerite)</th>
                                  <th className="p-4 text-xs font-bold text-orange-400 uppercase tracking-wider border-b border-white/10">DSR (Holerite)</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-white/5 bg-[#1A1F2B]">
                                {resultadoAuditoria.divergencias.map((div: any, idx: number) => (
                                  <tr key={idx} className="hover:bg-white/5 transition-colors">
                                    <td className="p-4 font-bold text-white">{div.nome}</td>
                                    <td className="p-4 font-bold text-blue-400">{div.faltas_escritorio}</td>
                                    <td className="p-4 font-bold text-blue-400">{div.dsr_escritorio}</td>
                                    <td className={`p-4 font-bold ${div.faltas_recibo !== div.faltas_escritorio ? 'text-red-500 underline' : 'text-orange-400'}`}>{div.faltas_recibo}</td>
                                    <td className={`p-4 font-bold ${div.dsr_recibo !== div.dsr_escritorio ? 'text-red-500 underline' : 'text-orange-400'}`}>{div.dsr_recibo}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* ========================================= */}
                {/* TELA 4: AUDITORIA DE TERMOS DE HORA EXTRA */}
                {/* ========================================= */}
                {modoFolha === 'convocacao' && (
                  <div className="fade-in py-4">
                    <div className="text-center flex flex-col items-center justify-center mb-10">
                      <div className="w-16 h-16 bg-purple-500/10 text-purple-500 rounded-full flex items-center justify-center mb-6"><CalendarRange className="w-8 h-8" /></div>
                      <h2 className={`text-2xl font-bold ${textColor} mb-2`}>Caça-Fantasmas: Absenteísmo em Hora Extra</h2>
                      <p className={`${textMuted} text-sm max-w-lg mx-auto`}>Faça o upload do <b>PDF Escaneado</b> contendo as assinaturas e o arquivo original do <b>SAP</b>. O robô vai descobrir sozinho a data, ler os nomes assinados e cruzar com as batidas do relógio.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-8">
                      {/* CAIXA 1: PDF DO SCANNER */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoPdfConvocacao ? 'border-purple-500 bg-purple-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-purple-500'}`}>
                         <input type="file" accept=".pdf" onChange={(e) => setArquivoPdfConvocacao(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoPdfConvocacao ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-purple-500 mb-3" />
                             <span className="text-purple-400 font-bold text-sm text-center line-clamp-1">{arquivoPdfConvocacao.name}</span>
                             <span className="text-slate-500 text-xs mt-1">Termo Lido com Sucesso.</span>
                           </>
                         ) : (
                           <>
                             <UploadCloud className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">1. PDF Assinado (.pdf)</span>
                             <span className="text-slate-500 text-xs mt-1 text-center">Arquivo gerado pela multifuncional</span>
                           </>
                         )}
                      </div>

                      {/* CAIXA 2: SAP */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoSapRpa ? 'border-purple-500 bg-purple-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-purple-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoSapRpa(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoSapRpa ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-purple-500 mb-3" />
                             <span className="text-purple-400 font-bold text-sm text-center line-clamp-1">{arquivoSapRpa.name}</span>
                             <span className="text-slate-500 text-xs mt-1">Espelho de Ponto pronto.</span>
                           </>
                         ) : (
                           <>
                             <Clock className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">2. Arquivo SAP (.xls)</span>
                             <span className="text-slate-500 text-xs mt-1 text-center">Exportação do mês correspondente</span>
                           </>
                         )}
                      </div>
                    </div>

                    <div className="flex justify-center mb-10">
                      <button onClick={handleAuditarConvocacao} disabled={processandoConvocacao || !arquivoPdfConvocacao || !arquivoSapRpa} className={`px-8 py-4 rounded-xl font-bold text-sm transition-all shadow-lg flex items-center gap-3 ${processandoConvocacao ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : (!arquivoPdfConvocacao || !arquivoSapRpa) ? 'bg-[#232936] text-slate-500 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-500 text-white hover:shadow-purple-500/20 hover:-translate-y-1'}`}>
                        {processandoConvocacao ? <Loader2 className="w-5 h-5 animate-spin" /> : <Activity className="w-5 h-5" />}
                        {processandoConvocacao ? 'Lendo PDF e varrendo SAP...' : 'AUDITAR PRESENÇAS E FALTAS'}
                      </button>
                    </div>

                    {/* TABELA DE RESULTADOS */}
                    {resultadoConvocacao && (
                      <div className="fade-in bg-[#1A1F2B] rounded-xl border border-white/10 p-6">
                        <div className="flex justify-between items-center mb-6">
                          <div>
                            <h3 className="text-lg font-bold text-white">Relatório de Presença Confirmada</h3>
                            <p className="text-slate-400 text-sm">Data da Convocação: <span className="text-purple-400 font-bold">{resultadoConvocacao.data_convocacao}</span> ({resultadoConvocacao.total_convocados} assinaturas lidas)</p>
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-1 gap-3">
                          {resultadoConvocacao.resultados.map((res: any, idx: number) => {
                            const faltou = res.status.includes("Faltou");
                            return (
                              <div key={idx} className={`flex justify-between items-center p-4 rounded-lg border ${faltou ? 'bg-red-500/10 border-red-500/20' : 'bg-emerald-500/10 border-emerald-500/20'}`}>
                                <div className="flex flex-col gap-1">
                                  <span className="font-bold text-white">{res.nome_normalizado}</span>
                                  <span className={`text-xs font-mono font-bold ${faltou ? 'text-red-400' : 'text-emerald-400'}`}>Relógio: {res.batidas}</span>
                                </div>
                                <span className={`px-4 py-2 rounded-lg font-bold text-sm ${faltou ? 'bg-red-500 text-white shadow-lg shadow-red-500/20' : 'bg-emerald-500/20 text-emerald-400'}`}>{res.status}</span>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ========================================= */}
                {/* TELA 5: LANÇAMENTO DE VALES / MÓVEIS      */}
                {/* ========================================= */}
                {modoFolha === 'vales' && (
                  <div className="fade-in py-4">
                    <div className="text-center flex flex-col items-center justify-center mb-10">
                      <div className="w-16 h-16 bg-orange-500/10 text-orange-500 rounded-full flex items-center justify-center mb-6"><ShoppingCart className="w-8 h-8" /></div>
                      <h2 className={`text-2xl font-bold ${textColor} mb-2`}>Robô RPA: Desconto de Móveis e Vales</h2>
                      <p className={`${textMuted} text-sm max-w-lg mx-auto`}>Suba o PDF do romaneio para o robô ler. Você poderá <b>revisar e corrigir o nome</b> antes de autorizar a injeção na planilha da contabilidade.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-8">
                      {/* CAIXA 1: PDF DO ROMANEIO */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoPdfVale ? 'border-orange-500 bg-orange-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-orange-500'}`}>
                         <input type="file" accept=".pdf" onChange={(e) => setArquivoPdfVale(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoPdfVale ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-orange-500 mb-3" />
                             <span className="text-orange-400 font-bold text-sm text-center line-clamp-1">{arquivoPdfVale.name}</span>
                           </>
                         ) : (
                           <>
                             <UploadCloud className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">1. Romaneio PDF</span>
                           </>
                         )}
                      </div>

                      {/* CAIXA 2: PLANILHA ESCRITORIO */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoBaseRpa ? 'border-orange-500 bg-orange-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-orange-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoBaseRpa(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoBaseRpa ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-orange-500 mb-3" />
                             <span className="text-orange-400 font-bold text-sm text-center line-clamp-1">{arquivoBaseRpa.name}</span>
                           </>
                         ) : (
                           <>
                             <Briefcase className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">2. Planilha Contabilidade (.xlsx)</span>
                           </>
                         )}
                      </div>
                    </div>

                    {/* BOTÃO DE LER PDF */}
                    {!dadosPreLista && (
                      <div className="flex justify-center mb-10">
                        <button onClick={handleExtrairVales} disabled={processandoVale || !arquivoPdfVale} className={`px-8 py-4 rounded-xl font-bold text-sm transition-all shadow-lg flex items-center gap-3 ${processandoVale ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : (!arquivoPdfVale) ? 'bg-[#232936] text-slate-500 cursor-not-allowed' : 'bg-[#232936] hover:bg-orange-600 hover:text-white text-orange-500 border border-orange-500 hover:shadow-orange-500/20'}`}>
                          {processandoVale ? <Loader2 className="w-5 h-5 animate-spin" /> : <Activity className="w-5 h-5" />}
                          1. LER DOCUMENTO (PRÉ-VISUALIZAR)
                        </button>
                      </div>
                    )}

                    {/* PAINEL DE REVISÃO E CONFIRMAÇÃO */}
                    {dadosPreLista && (
                      <div className="fade-in max-w-4xl mx-auto bg-[#1A1F2B] border border-orange-500/30 rounded-xl p-6 mb-8 shadow-2xl">
                        <div className="flex items-center gap-3 mb-6 border-b border-white/5 pb-4">
                          <AlertTriangle className="w-6 h-6 text-amber-500" />
                          <h3 className="text-lg font-bold text-white">Revisão do Lançamento</h3>
                          {dadosPreLista.parcelas > 1 && <span className="ml-auto bg-amber-500/20 text-amber-400 px-3 py-1 text-xs font-bold rounded">Dividido em {dadosPreLista.parcelas}x (Total: R$ {dadosPreLista.valor_original})</span>}
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                          <div>
                            <label className="block text-xs font-bold text-slate-400 mb-2 uppercase">Nome do Colaborador (Corrija se necessário)</label>
                            <input type="text" value={nomeEditado} onChange={(e) => setNomeEditado(e.target.value)} className="w-full bg-[#0E1218] border border-white/10 text-white px-4 py-3 rounded-lg focus:outline-none focus:border-orange-500" />
                            <span className="text-[10px] text-slate-500 mt-1 block">O robô procurará este nome exato na planilha Excel.</span>
                          </div>
                          <div>
                            <label className="block text-xs font-bold text-slate-400 mb-2 uppercase">Valor do Desconto (R$)</label>
                            <input type="text" value={valorEditado} onChange={(e) => setValorEditado(e.target.value)} className="w-full bg-[#0E1218] border border-white/10 text-emerald-400 font-bold px-4 py-3 rounded-lg focus:outline-none focus:border-orange-500" />
                          </div>
                        </div>

                        <div className="flex justify-end gap-4">
                          <button onClick={() => setDadosPreLista(null)} className="px-6 py-3 rounded-lg font-bold text-sm bg-transparent text-slate-400 hover:text-white hover:bg-white/5 transition-colors">Cancelar</button>
                          <button onClick={handleInjetarValesConfirmados} disabled={processandoVale || !arquivoBaseRpa} className={`px-8 py-3 rounded-lg font-bold text-sm transition-all shadow-lg flex items-center gap-2 ${processandoVale ? 'bg-slate-800 text-slate-500' : 'bg-orange-600 hover:bg-orange-500 text-white'}`}>
                            {processandoVale ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle2 className="w-5 h-5" />}
                            2. CONFIRMAR E LANÇAR NO EXCEL
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ========================================= */}
                {/* TELA 6: CONVÊNIO FARMÁCIA                 */}
                {/* ========================================= */}
                {modoFolha === 'farmacia' && (
                  <div className="fade-in py-4">
                    <div className="text-center flex flex-col items-center justify-center mb-10">
                      <div className="w-16 h-16 bg-pink-500/10 text-pink-500 rounded-full flex items-center justify-center mb-6"><Pill className="w-8 h-8" /></div>
                      <h2 className={`text-2xl font-bold ${textColor} mb-2`}>Robô RPA: Convênio Farmácia em Massa</h2>
                      <p className={`${textMuted} text-sm max-w-lg mx-auto`}>Anexe o Extrato da Farmácia <b>(.xls)</b> e a Planilha da Contabilidade. O robô vai varrer todos os nomes e injetar dezenas de valores simultaneamente na coluna correta.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-8">
                      {/* CAIXA 1: EXTRATO FARMÁCIA */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoExtratoFarmacia ? 'border-pink-500 bg-pink-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-pink-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoExtratoFarmacia(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoExtratoFarmacia ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-pink-500 mb-3" />
                             <span className="text-pink-400 font-bold text-sm text-center line-clamp-1">{arquivoExtratoFarmacia.name}</span>
                             <span className="text-slate-500 text-xs mt-1">Extrato pronto.</span>
                           </>
                         ) : (
                           <>
                             <UploadCloud className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">1. Extrato da Farmácia (.xls)</span>
                             <span className="text-slate-500 text-xs mt-1 text-center">Exportado direto do sistema da drogaria</span>
                           </>
                         )}
                      </div>

                      {/* CAIXA 2: PLANILHA ESCRITORIO */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoBaseRpa ? 'border-pink-500 bg-pink-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-pink-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoBaseRpa(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoBaseRpa ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-pink-500 mb-3" />
                             <span className="text-pink-400 font-bold text-sm text-center line-clamp-1">{arquivoBaseRpa.name}</span>
                             <span className="text-slate-500 text-xs mt-1">Planilha Base pronta.</span>
                           </>
                         ) : (
                           <>
                             <Briefcase className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">2. Planilha Contabilidade (.xlsx)</span>
                             <span className="text-slate-500 text-xs mt-1 text-center">A planilha oficial que vai pro contador</span>
                           </>
                         )}
                      </div>
                    </div>

                    <div className="flex justify-center">
                      <button onClick={handleGerarRpaFarmacia} disabled={processandoFarmacia || !arquivoExtratoFarmacia || !arquivoBaseRpa} className={`px-8 py-4 rounded-xl font-bold text-sm transition-all shadow-lg flex items-center gap-3 ${processandoFarmacia ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : (!arquivoExtratoFarmacia || !arquivoBaseRpa) ? 'bg-[#232936] text-slate-500 cursor-not-allowed' : 'bg-pink-600 hover:bg-pink-500 text-white hover:shadow-pink-500/20 hover:-translate-y-1'}`}>
                        {processandoFarmacia ? <Loader2 className="w-5 h-5 animate-spin" /> : <Bot className="w-5 h-5" />}
                        {processandoFarmacia ? 'Robô injetando descontos...' : 'INICIAR LANÇAMENTO EM MASSA'}
                      </button>
                    </div>

                  </div>
                )}

                {/* ========================================= */}
                {/* TELA 7: FECHAMENTO DE BÔNUS (RPA)         */}
                {/* ========================================= */}
                {modoFolha === 'bonus' && (
                  <div className="fade-in py-4">
                    <div className="text-center flex flex-col items-center justify-center mb-10">
                      <div className="w-16 h-16 bg-amber-500/10 text-amber-500 rounded-full flex items-center justify-center mb-6"><Award className="w-8 h-8" /></div>
                      <h2 className={`text-2xl font-bold ${textColor} mb-2`}>Robô RPA: Cálculo de Bônus</h2>
                      <p className={`${textMuted} text-sm max-w-2xl mx-auto`}>Anexe o espelho original do <b>SAP</b> e a sua <b>Planilha de Bônus</b>. O sistema vai rastrear Faltas, Meio Períodos e Atestados, calcular o percentual exato de perda (25%, 50% ou 100%) e preencher automaticamente a coluna "Desconto (%)" justificando o motivo.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-8">
                      {/* CAIXA 1: SAP */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoSapRpa ? 'border-amber-500 bg-amber-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-amber-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoSapRpa(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoSapRpa ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-amber-500 mb-3" />
                             <span className="text-amber-400 font-bold text-sm text-center line-clamp-1">{arquivoSapRpa.name}</span>
                             <span className="text-slate-500 text-xs mt-1">Arquivo SAP pronto.</span>
                           </>
                         ) : (
                           <>
                             <UploadCloud className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">1. Arquivo SAP (.xls)</span>
                             <span className="text-slate-500 text-xs mt-1 text-center">De onde o robô vai puxar os atrasos e faltas</span>
                           </>
                         )}
                      </div>

                      {/* CAIXA 2: PLANILHA BONUS */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoBaseRpa ? 'border-amber-500 bg-amber-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-amber-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoBaseRpa(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoBaseRpa ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-amber-500 mb-3" />
                             <span className="text-amber-400 font-bold text-sm text-center line-clamp-1">{arquivoBaseRpa.name}</span>
                             <span className="text-slate-500 text-xs mt-1">Planilha de Bônus pronta.</span>
                           </>
                         ) : (
                           <>
                             <Briefcase className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">2. Sua Planilha de Bônus (.xlsx)</span>
                             <span className="text-slate-500 text-xs mt-1 text-center">A que tem a coluna "Desconto (%)" e "Motivo"</span>
                           </>
                         )}
                      </div>
                    </div>

                    <div className="flex justify-center">
                      <button onClick={handleGerarRpaBonus} disabled={gerandoRpa || !arquivoSapRpa || !arquivoBaseRpa} className={`px-8 py-4 rounded-xl font-bold text-sm transition-all shadow-lg flex items-center gap-3 ${gerandoRpa ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : (!arquivoSapRpa || !arquivoBaseRpa) ? 'bg-[#232936] text-slate-500 cursor-not-allowed' : 'bg-amber-600 hover:bg-amber-500 text-white hover:shadow-amber-500/20 hover:-translate-y-1'}`}>
                        {gerandoRpa ? <Loader2 className="w-5 h-5 animate-spin" /> : <Bot className="w-5 h-5" />}
                        {gerandoRpa ? 'Calculando limites e injetando bônus...' : 'INICIAR CÁLCULO E BAIXAR PLANILHA'}
                      </button>
                    </div>

                  </div>
                )}

                {/* ========================================= */}
                {/* TELA 8: AUDITOR DE BÔNUS (PDF UCHOA / XLS IBIRA)*/}
                {/* ========================================= */}
                {modoFolha === 'auditor_bonus' && (
                  <div className="fade-in py-4">
                    <div className="text-center flex flex-col items-center justify-center mb-10">
                      <div className="w-16 h-16 bg-amber-500/10 text-amber-500 rounded-full flex items-center justify-center mb-6"><AlertOctagon className="w-8 h-8" /></div>
                      <h2 className={`text-2xl font-bold ${textColor} mb-2`}>Auditoria Cruzada: Bônus vs Espelho SAP</h2>
                      <p className={`${textMuted} text-sm max-w-lg mx-auto`}>Anexe o <b>Espelho de Ponto (PDF ou XLS)</b> e a sua <b>Planilha de Bônus Finalizada</b>. O robô vai ler a extensão do arquivo automaticamente, calcular os 100%, 50% e 25% e apontar quem está divergente.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-8">
                      {/* CAIXA 1: PDF/XLS DO ESPELHO SAP */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoPdfBonus ? 'border-amber-500 bg-amber-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-amber-500'}`}>
                         <input type="file" accept=".pdf,.xls,.xlsx" onChange={(e) => setArquivoPdfBonus(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoPdfBonus ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-amber-500 mb-3" />
                             <span className="text-amber-400 font-bold text-sm text-center line-clamp-1">{arquivoPdfBonus.name}</span>
                           </>
                         ) : (
                           <>
                             <UploadCloud className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">1. Espelho Ponto (PDF ou XLS)</span>
                           </>
                         )}
                      </div>

                      {/* CAIXA 2: PLANILHA DE BÔNUS */}
                      <div className={`relative border-2 border-dashed rounded-xl p-8 transition-all flex flex-col items-center justify-center ${arquivoBaseRpa ? 'border-amber-500 bg-amber-500/5' : 'border-slate-600 bg-[#1A1F2B] hover:border-amber-500'}`}>
                         <input type="file" accept=".xls,.xlsx" onChange={(e) => setArquivoBaseRpa(e.target.files ? e.target.files[0] : null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                         {arquivoBaseRpa ? (
                           <>
                             <CheckCircle2 className="w-8 h-8 text-amber-500 mb-3" />
                             <span className="text-amber-400 font-bold text-sm text-center line-clamp-1">{arquivoBaseRpa.name}</span>
                           </>
                         ) : (
                           <>
                             <Briefcase className="w-8 h-8 text-slate-500 mb-3" />
                             <span className="text-slate-300 font-bold text-sm text-center">2. Sua Planilha Bônus (.xlsx)</span>
                           </>
                         )}
                      </div>
                    </div>

                    <div className="flex justify-center mb-10">
                      <button onClick={handleAuditarBonusUniversal} disabled={processandoAuditoriaBonus || !arquivoPdfBonus || !arquivoBaseRpa} className={`px-8 py-4 rounded-xl font-bold text-sm transition-all shadow-lg flex items-center gap-3 ${processandoAuditoriaBonus ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : (!arquivoPdfBonus || !arquivoBaseRpa) ? 'bg-[#232936] text-slate-500 cursor-not-allowed' : 'bg-amber-600 hover:bg-amber-500 text-white hover:shadow-amber-500/20 hover:-translate-y-1'}`}>
                        {processandoAuditoriaBonus ? <Loader2 className="w-5 h-5 animate-spin" /> : <Activity className="w-5 h-5" />}
                        {processandoAuditoriaBonus ? 'Auditando marcações de ponto...' : 'INICIAR AUDITORIA DE BÔNUS'}
                      </button>
                    </div>

                    {/* RESULTADO DA AUDITORIA */}
                    {resultadoAuditoriaBonus && (
                      <div className="fade-in bg-[#1A1F2B] rounded-xl border border-white/10 p-6">
                        <div className="flex justify-between items-center mb-6">
                          <div>
                            <h3 className="text-lg font-bold text-white">Relatório de Divergências</h3>
                            <p className="text-slate-400 text-sm">Foram lidos {resultadoAuditoriaBonus.total_auditados} espelhos de ponto.</p>
                          </div>
                        </div>
                        
                        {resultadoAuditoriaBonus.divergencias.length === 0 ? (
                          <div className="bg-emerald-500/10 border border-emerald-500/30 p-6 rounded-xl text-center">
                            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                            <h4 className="text-emerald-400 font-bold text-lg">Bônus Auditado com Sucesso!</h4>
                            <p className="text-emerald-500/70 text-sm mt-1">Os descontos da planilha batem perfeitamente com os horários batidos no SAP.</p>
                          </div>
                        ) : (
                          <div className="overflow-x-auto rounded-xl border border-white/10">
                            <table className="w-full text-left border-collapse">
                              <thead>
                                <tr className="bg-[#232936]">
                                  <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-white/10">Colaborador</th>
                                  <th className="p-4 text-xs font-bold text-blue-400 uppercase tracking-wider border-b border-white/10">O que está na Planilha</th>
                                  <th className="p-4 text-xs font-bold text-orange-400 uppercase tracking-wider border-b border-white/10">Deveria ser (Pelo Ponto)</th>
                                  <th className="p-4 text-xs font-bold text-orange-400 uppercase tracking-wider border-b border-white/10">Motivo Encontrado no Ponto</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-white/5 bg-[#1A1F2B]">
                                {resultadoAuditoriaBonus.divergencias.map((div: any, idx: number) => (
                                  <tr key={idx} className="hover:bg-white/5 transition-colors">
                                    <td className="p-4 font-bold text-white">{div.nome}</td>
                                    <td className="p-4 font-bold text-red-500 line-through">{div.desc_planilha} de desconto</td>
                                    <td className="p-4 font-bold text-orange-400">{div.desc_pdf} de desconto</td>
                                    <td className="p-4 text-sm text-slate-300">{div.detalhes_pdf}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}

export default App;
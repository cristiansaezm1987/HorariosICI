// --- STATE MANAGEMENT ---
let activeTab = 'dashboard';
let dataLoaded = false;
let globalFilters = {
    carrera: '',
    jornada: ''
};

let allDocentes = [];
let allSalas = [];
let allAsignaturas = []; // raw data for client-side filtering
let programasAsignaturas = []; // fetched from /api/programas
let documentosInstitucionales = []; // fetched from /api/documentos
let selectedDocente = null;
let selectedSala = null;
let selectedNivel = '';
let allFiltersData = null; // Store global filters data for the overlay modal
let overlayState = {
    active: false,
    carrera: '',
    nivel: '',
    seccion: ''
};
// Track Chart.js instances so they can be destroyed on re-render
let chartInstances = {};

// Asignaturas filter state
let asignaturaFilters = {
    query: '',
    nivel: '',
    tipo: '',
    seccion: '',
    sort: ''
};

// Standard schedule blocks:
const SCHEDULE_BLOCKS = [
    { label: 'Bloque 1', times: '08:00 - 08:40', range: [800, 840] },
    { label: 'Bloque 2', times: '08:41 - 09:20', range: [841, 920] },
    { label: 'Bloque 3', times: '09:30 - 10:10', range: [930, 1010] },
    { label: 'Bloque 4', times: '10:11 - 10:50', range: [1011, 1050] },
    { label: 'Bloque 5', times: '11:00 - 11:40', range: [1100, 1140] },
    { label: 'Bloque 6', times: '11:41 - 12:20', range: [1141, 1220] },
    { label: 'Bloque 7', times: '12:30 - 13:10', range: [1230, 1310] },
    { label: 'Bloque 8', times: '13:11 - 13:50', range: [1311, 1350] },
    { label: 'Bloque 9', times: '14:00 - 14:40', range: [1400, 1440] },
    { label: 'Bloque 10', times: '14:41 - 15:20', range: [1441, 1520] },
    { label: 'Bloque 11', times: '15:30 - 16:10', range: [1530, 1610] },
    { label: 'Bloque 12', times: '16:11 - 16:50', range: [1611, 1650] },
    { label: 'Bloque 13', times: '17:00 - 17:40', range: [1700, 1740] },
    { label: 'Bloque 14', times: '17:41 - 18:20', range: [1741, 1820] }
];

const WEEKDAYS = [
    { key: 'LUNES', label: 'Lunes' },
    { key: 'MARTES', label: 'Martes' },
    { key: 'MIERCOLES', label: 'Miércoles' },
    { key: 'JUEVES', label: 'Jueves' },
    { key: 'VIERNES', label: 'Viernes' }
];

// Helper to check if a class session overlaps with a schedule block
function isSessionInBlock(session, block) {
    if (!session.HORA_INCIO || !session.HORA_FIN) return false;
    const sStart = parseInt(session.HORA_INCIO);
    const sEnd = parseInt(session.HORA_FIN);
    const [bStart, bEnd] = block.range;
    return Math.max(sStart, bStart) < Math.min(sEnd, bEnd);
}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    initApp();
});
            if (grid) {
                grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #e11d48;"><i class="fa-solid fa-triangle-exclamation"></i> Error al cargar programas (Código ${response.status}). Esto puede deberse a que el servidor remoto (Vercel) no tiene acceso a la carpeta local C: de tu computador.</div>`;
            }
        }
    } catch (error) {
        console.error('Error loading programs:', error);
        const grid = document.getElementById('programas-grid');
        if (grid) {
            grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #e11d48;"><i class="fa-solid fa-triangle-exclamation"></i> Error de conexión: ${error.message}</div>`;
        }
    }
    
    document.getElementById('search-programas')?.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = programasAsignaturas.filter(p => p.filename.toLowerCase().includes(term));
        renderProgramasGrid(filtered);
    });
}

function renderProgramasGrid(programas) {
    const grid = document.getElementById('programas-grid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    if (programas.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #64748b;">No se encontraron programas.</div>';
        return;
    }
    
    // Group by folder
    const byFolder = {};
    programas.forEach(p => {
        if (!byFolder[p.folder]) byFolder[p.folder] = [];
        byFolder[p.folder].push(p);
    });
    
    // Sort folders
    const folders = Object.keys(byFolder).sort();
    
    folders.forEach(folder => {
        const section = document.createElement('div');
        section.style.gridColumn = '1 / -1';
        section.innerHTML = `<h3 style="margin-top: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 5px;">${folder}</h3>`;
        grid.appendChild(section);
        
        byFolder[folder].sort((a,b) => a.filename.localeCompare(b.filename)).forEach(p => {
            const card = document.createElement('div');
            card.style.border = '1px solid var(--border-color)';
            card.style.borderRadius = '6px';
            card.style.padding = '15px';
            card.style.display = 'flex';
            card.style.alignItems = 'center';
            card.style.gap = '15px';
            card.style.background = '#f8fafc';
            
            card.innerHTML = `
                <i class="fa-solid fa-file-pdf" style="font-size: 24px; color: #e11d48;"></i>
                <div style="flex-grow: 1; min-width: 0;">
                    <div style="font-weight: 500; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.filename}">${p.filename}</div>
                </div>
                <a href="/api/programas/download?path=${encodeURIComponent(p.path)}" class="btn-pdf" style="padding: 6px 12px; font-size: 0.8rem; text-decoration: none;"><i class="fa-solid fa-download"></i> Descargar</a>
            `;
            grid.appendChild(card);
        });
    });
}

async function loadDocumentos() {
    try {
        const response = await fetch('/api/documentos?_t=' + Date.now());
        if (response.ok) {
            documentosInstitucionales = await response.json();
            renderDocumentosGrid(documentosInstitucionales);
        } else {
            const grid = document.getElementById('documentos-grid');
            if (grid) {
                grid.innerHTML = \<div style=\"grid-column: 1 / -1; text-align: center; padding: 40px; color: #e11d48;\"><i class=\"fa-solid fa-triangle-exclamation\"></i> Error al cargar documentos.</div>\;
            }
        }
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

function renderDocumentosGrid(documentos) {
    const grid = document.getElementById('documentos-grid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    if (documentos.length === 0) {
        grid.innerHTML = \<div style=\"grid-column: 1 / -1; text-align: center; padding: 40px; color: #64748b;\">No se encontraron documentos en el repositorio.</div>\;
        return;
    }
    
    documentos.sort((a,b) => a.filename.localeCompare(b.filename)).forEach(doc => {
        const card = document.createElement('div');
        card.style.border = '1px solid var(--border-color)';
        card.style.borderRadius = '6px';
        card.style.padding = '15px';
        card.style.display = 'flex';
        card.style.alignItems = 'center';
        card.style.gap = '15px';
        card.style.background = '#f8fafc';
        
        card.innerHTML = \
            <i class=\"fa-solid fa-file-contract\" style=\"font-size: 24px; color: var(--secondary-color);\"></i>
            <div style=\"flex-grow: 1; min-width: 0;\">
                <div style=\"font-weight: 500; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;\" title=\"\\">\</div>
            </div>
            <a href=\"/static/documentos/\\" download=\"\\" class=\"btn-pdf\" style=\"background: var(--secondary-color); padding: 6px 12px; font-size: 0.8rem; text-decoration: none;\"><i class=\"fa-solid fa-download\"></i> Descargar</a>
        \;
        grid.appendChild(card);
    });
}


function renderDocenteDocumentos() {
    const card = document.getElementById('docente-documentos-card');
    const list = document.getElementById('docente-documentos-list');
    const enviarTodoCard = document.getElementById('docente-enviar-todo-card');
    
    if (!card || !list || !enviarTodoCard) return;
    
    if (!documentosInstitucionales || documentosInstitucionales.length === 0) {
        card.style.display = 'none';
        enviarTodoCard.style.display = 'none';
        return;
    }
    
    list.innerHTML = '';
    
    documentosInstitucionales.forEach(doc => {
        const item = document.createElement('div');
        item.style.border = '1px solid var(--border-color)';
        item.style.padding = '10px 15px';
        item.style.borderRadius = '4px';
        item.style.display = 'flex';
        item.style.justifyContent = 'space-between';
        item.style.alignItems = 'center';
        item.style.background = 'white';
        
        item.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fa-solid fa-file-contract" style="color: var(--secondary-color); font-size: 1.2rem;"></i>
                <span style="font-weight: 500; font-size: 0.9rem;">${doc.filename}</span>
            </div>
            <a href="/static/documentos/${doc.path.replace(/\\/g, '/')}" download="${doc.filename}" class="btn-pdf" style="background: var(--secondary-color); font-size: 0.8rem; padding: 4px 10px;"><i class="fa-solid fa-download"></i></a>
        `;
        list.appendChild(item);
    });
    
    card.style.display = 'block';
    enviarTodoCard.style.display = 'block';
}

document.getElementById('btn-email-documentos')?.addEventListener('click', async () => {
    if (!documentosInstitucionales || documentosInstitucionales.length === 0) {
        showToast('No hay documentos institucionales disponibles', 'error');
        return;
    }
    await sendDocumentosEmail();
});

async function sendDocumentosEmail() {
    const email = prompt('Ingrese el correo al que desea enviar los documentos institucionales:');
    if (email === null) return;
    
    if (email) {
        try {
            await copyToClipboard(email);
            showToast('Correo copiado al portapapeles. Pégalo en tu cliente de correo (Ctrl+V).', 'success');
        } catch (err) {
            console.error('Failed to copy email: ', err);
            showToast('No se pudo copiar el correo automáticamente. Por favor, escríbelo manualmente.', 'error');
        }
    }
    
    try {
        const filePromises = documentosInstitucionales.map(async doc => {
            const url = `/static/documentos/${doc.path.replace(/\\/g, '/')}`;
            const res = await fetch(url);
            if (!res.ok) throw new Error(`Failed to fetch ${doc.filename}`);
            const blob = await res.blob();
            return new File([blob], doc.filename, { type: 'application/pdf' });
        });
        
        const files = await Promise.all(filePromises);
        
        if (navigator.canShare && navigator.canShare({ files: files })) {
            await navigator.share({
                title: 'Documentos Institucionales',
                text: 'Adjunto envío documentos institucionales.',
                files: files
            });
        } else {
            showToast('Tu navegador no soporta adjuntar múltiples archivos automáticamente (prueba en móvil o Safari/Edge modernos).', 'error');
        }
    } catch(err) {
        console.error(err);
        showToast('Error preparando los archivos: ' + err.message, 'error');
    }
}

document.getElementById('btn-enviar-todo')?.addEventListener('click', async () => {
    if (!selectedDocente) return;
    await sendTodoEmail(selectedDocente);
});

async function sendTodoEmail(docente) {
    const email = prompt('Ingrese el correo del docente para enviar todo consolidado:');
    if (email === null) return;
    
    const statusToast = document.createElement('div');
    statusToast.className = 'toast info';
    statusToast.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Preparando todos los archivos (Horario, Programas, Documentos)...';
    document.getElementById('toast-container').appendChild(statusToast);
    
    if (email) {
        try {
            await copyToClipboard(email);
            showToast('Correo copiado al portapapeles. Pégalo en tu cliente de correo (Ctrl+V).', 'success');
        } catch (err) {}
    }
    
    try {
        const allFiles = [];
        
        // 1. Horario
        const element = document.getElementById('docente-timetable');
        const opt = {
            margin:       10,
            filename:     `Horario_${docente.DOCENTE.replace(/ /g, '_')}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2, useCORS: true },
            jsPDF:        { unit: 'mm', format: 'a4', orientation: 'landscape' }
        };
        const pdfWorker = await html2pdf().set(opt).from(element).output('blob');
        allFiles.push(new File([pdfWorker], opt.filename, { type: 'application/pdf' }));
        
        // 2. Programas
        const card = document.getElementById('docente-programas-card');
        if (card.style.display !== 'none' && currentMatchedProgramas && currentMatchedProgramas.length > 0) {
            const progPromises = currentMatchedProgramas.map(async p => {
                const url = `/api/programas/download?path=${encodeURIComponent(p.path)}`;
                const res = await fetch(url);
                if (!res.ok) throw new Error(`Failed to fetch ${p.filename}`);
                const blob = await res.blob();
                return new File([blob], p.filename, { type: 'application/pdf' });
            });
            const progFiles = await Promise.all(progPromises);
            allFiles.push(...progFiles);
        }
        
        // 3. Documentos
        if (documentosInstitucionales && documentosInstitucionales.length > 0) {
            const docPromises = documentosInstitucionales.map(async doc => {
                const url = `/static/documentos/${doc.path.replace(/\\/g, '/')}`;
                const res = await fetch(url);
                if (!res.ok) throw new Error(`Failed to fetch ${doc.filename}`);
                const blob = await res.blob();
                return new File([blob], doc.filename, { type: 'application/pdf' });
            });
            const docFiles = await Promise.all(docPromises);
            allFiles.push(...docFiles);
        }
        
        statusToast.remove();
        
        if (navigator.canShare && navigator.canShare({ files: allFiles })) {
            await navigator.share({
                title: `Consolidado Docente - ${docente.DOCENTE}`,
                text: `Estimado/a ${docente.DOCENTE}, adjunto encontrará su horario académico, programas de asignatura y reglamentación institucional.`,
                files: allFiles
            });
        } else {
            showToast('Tu navegador no soporta adjuntar múltiples archivos automáticamente. Descarga los archivos individualmente.', 'error');
        }
    } catch(err) {
        console.error(err);
        statusToast.remove();
        showToast('Error preparando los archivos consolidado: ' + err.message, 'error');
    }
}

document.getElementById('search-documentos')?.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    if (!documentosInstitucionales) return;
    
    const filtered = documentosInstitucionales.filter(doc => doc.filename.toLowerCase().includes(q));
    renderDocumentosGrid(filtered);
});

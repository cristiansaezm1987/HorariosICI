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
let selectedDocente = null;
let selectedSala = null;
let selectedNivel = '';
// Track Chart.js instances so they can be destroyed on re-render
let chartInstances = {};

// Asignaturas filter state
let asignaturaFilters = {
    query: '',
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

function initApp() {
    checkDatabaseStatus();
}

// Check database status
function checkDatabaseStatus() {
    const statusDiv = document.getElementById('load-status');
    statusDiv.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Verificando datos...';
    
    fetch('/api/summary')
        .then(res => res.json())
        .then(data => {
            if (data.success && !data.empty) {
                dataLoaded = true;
                statusDiv.className = 'header-status loaded';
                statusDiv.innerHTML = `<i class="fa-solid fa-circle-check"></i> Planificación Cargada (${data.metrics.total_nrcs} NRCs)`;
                
                document.getElementById('empty-state').style.display = 'none';
                
                // Show filters and load selectors
                loadGlobalFilters();
                
                // Load current tab
                switchTab(activeTab);
            } else {
                dataLoaded = false;
                statusDiv.className = 'header-status empty';
                statusDiv.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Sin datos';
                
                // Show empty state and hide contents
                document.getElementById('empty-state').style.display = 'block';
                hideAllTabContents();
            }
        })
        .catch(err => {
            console.error('Error fetching summary:', err);
            showToast('Error al conectar con el servidor.', 'error');
        });
}

function hideAllTabContents() {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
}

// --- EVENT LISTENERS ---
function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.nav-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const tabName = button.getAttribute('data-tab');
            if (dataLoaded || tabName === 'dashboard') {
                document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                switchTab(tabName);
            } else {
                showToast('Primero debes cargar un archivo de planificación CSV.', 'info');
            }
        });
    });

    // File Upload Setup
    const btnSelectFile = document.getElementById('btn-select-file');
    const fileInput = document.getElementById('csv-file-input');
    const fileNameDisplay = document.getElementById('file-name-display');
    const uploadProgress = document.getElementById('upload-progress');
    const progressBarFill = uploadProgress.querySelector('.progress-bar-fill');

    btnSelectFile.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            const files = Array.from(fileInput.files);
            const fileNames = files.map(f => f.name).join(', ');
            fileNameDisplay.textContent = fileNames;
            uploadCSV(files);
        }
    });

    // Drag and Drop files onto the upload box
    const uploadBox = document.querySelector('.upload-box');
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadBox.addEventListener(eventName, (e) => {
            e.preventDefault();
            uploadBox.style.borderColor = 'var(--primary-color)';
            uploadBox.style.backgroundColor = 'rgba(218, 41, 28, 0.04)';
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadBox.addEventListener(eventName, (e) => {
            e.preventDefault();
            uploadBox.style.borderColor = 'var(--border-color)';
            uploadBox.style.backgroundColor = 'var(--body-bg)';
        }, false);
    });

    uploadBox.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = Array.from(dt.files).filter(f => f.name.endsWith('.csv'));
        if (files.length > 0) {
            const fileNames = files.map(f => f.name).join(', ');
            fileNameDisplay.textContent = fileNames;
            uploadCSV(files);
        } else {
            showToast('Por favor, arrastra solo archivos CSV válidos.', 'error');
        }
    });

    // Global filters change
    document.getElementById('filter-carrera').addEventListener('change', (e) => {
        globalFilters.carrera = e.target.value;
        refreshActiveTab();
    });

    document.getElementById('filter-jornada').addEventListener('change', (e) => {
        globalFilters.jornada = e.target.value;
        refreshActiveTab();
    });

    document.getElementById('btn-clear-filters').addEventListener('click', () => {
        document.getElementById('filter-carrera').value = '';
        document.getElementById('filter-jornada').value = '';
        globalFilters.carrera = '';
        globalFilters.jornada = '';
        showToast('Filtros globales limpiados.', 'info');
        refreshActiveTab();
    });

    // Client-side search in lists
    document.getElementById('search-asignatura').addEventListener('input', (e) => {
        asignaturaFilters.query = e.target.value;
        applyAsignaturaFilters();
    });

    // Advanced asignatura filters
    document.getElementById('filter-asignatura-tipo').addEventListener('change', (e) => {
        asignaturaFilters.tipo = e.target.value;
        applyAsignaturaFilters();
    });

    document.getElementById('filter-asignatura-seccion').addEventListener('input', (e) => {
        asignaturaFilters.seccion = e.target.value;
        applyAsignaturaFilters();
    });

    document.getElementById('sort-asignaturas').addEventListener('change', (e) => {
        asignaturaFilters.sort = e.target.value;
        applyAsignaturaFilters();
    });

    document.getElementById('search-docente').addEventListener('input', (e) => {
        filterDocentesList(e.target.value);
    });

    document.getElementById('search-sala').addEventListener('input', (e) => {
        filterSalasList(e.target.value);
    });

    // Level selector
    document.getElementById('select-nivel').addEventListener('change', (e) => {
        selectedNivel = e.target.value;
        if (selectedNivel) {
            loadNivelSchedule(selectedNivel);
        } else {
            document.getElementById('nivel-schedule-card').style.display = 'none';
        }
    });

    // PDF export buttons
    document.getElementById('btn-pdf-asignaturas').addEventListener('click', () => {
        exportPDF('asignaturas');
    });
    document.getElementById('btn-pdf-docente').addEventListener('click', () => {
        exportPDF('docente');
    });
    document.getElementById('btn-pdf-nivel').addEventListener('click', () => {
        exportPDF('nivel');
    });
    document.getElementById('btn-pdf-sala').addEventListener('click', () => {
        exportPDF('sala');
    });
    
    // --- DISPLAY OPTIONS LISTENERS ---
    function toggleDisplayOption(checkboxId, cssClass) {
        const chk = document.getElementById(checkboxId);
        if (chk) {
            chk.addEventListener('change', (e) => {
                if (e.target.checked) {
                    document.body.classList.remove(cssClass);
                } else {
                    document.body.classList.add(cssClass);
                }
            });
        }
    }
    
    toggleDisplayOption('chk-show-subject', 'hide-subject');
    toggleDisplayOption('chk-show-nrc', 'hide-nrc');
    toggleDisplayOption('chk-show-time', 'hide-time');
    toggleDisplayOption('chk-show-sala', 'hide-sala');
    toggleDisplayOption('chk-show-docente', 'hide-docente');
    toggleDisplayOption('chk-show-tipo', 'hide-tipo');

    // EXPORT ALL NIVELES PDF
    document.getElementById('btn-pdf-all-niveles')?.addEventListener('click', exportAllNivelesPDF);
}

// --- FILE UPLOAD LOGIC ---
function uploadCSV(files) {
    const uploadProgress = document.getElementById('upload-progress');
    const progressBarFill = uploadProgress.querySelector('.progress-bar-fill');
    
    uploadProgress.style.display = 'block';
    progressBarFill.style.width = '0%';
    
    const formData = new FormData();
    // Support either single file or array of files
    if (Array.isArray(files) || files instanceof FileList) {
        for(let i=0; i<files.length; i++) {
            formData.append('file', files[i]);
        }
    } else {
        formData.append('file', files);
    }
    
    // Perform upload
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload', true);
    
    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            progressBarFill.style.width = percentComplete + '%';
        }
    };
    
    xhr.onload = () => {
        uploadProgress.style.display = 'none';
        
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.success) {
                showToast(response.message, 'success');
                // Reset state variables
                selectedDocente = null;
                selectedSala = null;
                selectedNivel = '';
                
                checkDatabaseStatus();
            } else {
                showToast(response.message || 'Error al procesar archivo.', 'error');
            }
        } else {
            showToast('Error de comunicación con el servidor.', 'error');
        }
    };
    
    xhr.onerror = () => {
        uploadProgress.style.display = 'none';
        showToast('Error de conexión al subir el archivo.', 'error');
    };
    
    xhr.send(formData);
}

// --- TAB SWITCHING AND REFRESH ---
function switchTab(tabName) {
    activeTab = tabName;
    hideAllTabContents();
    
    const tabEl = document.getElementById(`tab-${tabName}`);
    if (tabEl) tabEl.classList.add('active');
    
    if (!dataLoaded) return;
    
    if (tabName === 'dashboard') {
        loadDashboard();
    } else if (tabName === 'asignaturas') {
        loadAsignaturas();
    } else if (tabName === 'docentes') {
        loadDocentes();
    } else if (tabName === 'niveles') {
        // Dropdown populated in loadGlobalFilters, just reset selection
        document.getElementById('select-nivel').value = selectedNivel;
        if (selectedNivel) {
            loadNivelSchedule(selectedNivel);
        } else {
            document.getElementById('nivel-schedule-card').style.display = 'none';
        }
    } else if (tabName === 'salas') {
        loadSalas();
    }
}

function refreshActiveTab() {
    switchTab(activeTab);
}

// --- POPULATE SELECT FILTERS ---
function loadGlobalFilters() {
    fetch('/api/filters')
        .then(res => res.json())
        .then(data => {
            if (data.success && !data.empty) {
                // Carrera filter
                const selectCarrera = document.getElementById('filter-carrera');
                const prevCarreraVal = selectCarrera.value;
                selectCarrera.innerHTML = '<option value="">Todas las carreras</option>';
                data.carreras.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c;
                    opt.textContent = c;
                    selectCarrera.appendChild(opt);
                });
                selectCarrera.value = prevCarreraVal;
                globalFilters.carrera = prevCarreraVal;

                // Jornada filter
                const selectJornada = document.getElementById('filter-jornada');
                const prevJornadaVal = selectJornada.value;
                selectJornada.innerHTML = '<option value="">Todas</option>';
                data.jornadas.forEach(j => {
                    const opt = document.createElement('option');
                    opt.value = j;
                    opt.textContent = j === 'D' ? 'Diurna' : j === 'V' ? 'Vespertina' : j;
                    selectJornada.appendChild(opt);
                });
                selectJornada.value = prevJornadaVal;
                globalFilters.jornada = prevJornadaVal;

                // Nivel selector in Tab Niveles
                const selectNivel = document.getElementById('select-nivel');
                const prevNivelVal = selectNivel.value;
                selectNivel.innerHTML = '<option value="">-- Seleccionar Nivel --</option>';
                
                if (data.niveles && data.niveles_secciones) {
                    data.niveles.forEach(n => {
                        // General Nivel option
                        const optGroup = document.createElement('option');
                        optGroup.value = n;
                        optGroup.textContent = `Nivel ${n} (Todas las Secciones)`;
                        optGroup.style.fontWeight = 'bold';
                        selectNivel.appendChild(optGroup);
                        
                        // Specific Seccion options
                        const sectionsForLevel = data.niveles_secciones.filter(ns => ns.nivel === n);
                        if (sectionsForLevel.length > 1) {
                            sectionsForLevel.forEach(ns => {
                                const opt = document.createElement('option');
                                opt.value = `${n}|${ns.seccion}`;
                                opt.innerHTML = `&nbsp;&nbsp;&nbsp;↳ Nivel ${n} - Grupo ${ns.seccion}`;
                                selectNivel.appendChild(opt);
                            });
                        }
                    });
                }
                
                selectNivel.value = prevNivelVal;
                selectedNivel = prevNivelVal;
            }
        })
        .catch(err => console.error('Error loading filters:', err));
}

// --- TAB 1: DASHBOARD ---
function loadDashboard() {
    fetch('/api/summary')
        .then(res => res.json())
        .then(data => {
            if (data.success && !data.empty) {
                // Populate KPIs
                document.getElementById('metric-nrcs').textContent = data.metrics.total_nrcs;
                document.getElementById('metric-docentes').textContent = data.metrics.total_docentes;
                document.getElementById('metric-salas').textContent = data.metrics.total_salas;
                document.getElementById('metric-horas').textContent = data.metrics.total_horas + ' hrs';

                // Populate Cupos vs Inscritos Progress Bar
                const cupos = data.metrics.total_cupos;
                const inscritos = data.metrics.total_inscritos;
                const disponibles = data.metrics.total_disponibles;
                const percent = cupos > 0 ? Math.round((inscritos / cupos) * 100) : 0;

                document.getElementById('val-total-cupos').textContent = cupos;
                document.getElementById('val-total-inscritos').textContent = inscritos;
                document.getElementById('val-total-disponibles').textContent = disponibles;
                document.getElementById('matricula-percentage').textContent = `${percent}% de ocupación de cupos`;
                document.getElementById('matricula-progress-fill').style.width = `${percent}%`;

                const typeNames = {
                    'TEO': 'Teoría / Cátedra',
                    'AYU': 'Ayudantía',
                    'LAB': 'Laboratorio',
                    'TER': 'Terreno'
                };

                // --- Panel 1: Horas por tipo ---
                const horasList = document.getElementById('horas-por-tipo-list');
                horasList.innerHTML = '';

                // Order: TEO, LAB, AYU, TER, others
                const tipoOrder = ['TEO', 'LAB', 'AYU', 'TER'];
                const horasEntries = Object.entries(data.horas_por_tipo || {})
                    .filter(([t]) => t !== 'APM')
                    .sort((a, b) => {
                        const ia = tipoOrder.indexOf(a[0]);
                        const ib = tipoOrder.indexOf(b[0]);
                        return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
                    });

                const totalHorasTipos = horasEntries.reduce((s, [, h]) => s + h, 0);

                horasEntries.forEach(([type, horas]) => {
                    const item = document.createElement('div');
                    item.className = 'breakdown-item';
                    const name = typeNames[type] || type;
                    const pct = totalHorasTipos > 0 ? Math.round((horas / totalHorasTipos) * 100) : 0;
                    item.innerHTML = `
                        <div class="breakdown-info" style="flex:1; min-width:0;">
                            <span class="breakdown-tag badge-type ${type.toLowerCase()}">${type}</span>
                            <span class="breakdown-name">${name}</span>
                        </div>
                        <div style="display:flex; flex-direction:column; align-items:flex-end; gap:2px; min-width:90px;">
                            <span class="breakdown-stats"><strong>${horas}</strong> hrs</span>
                            <div style="width:80px; height:4px; background:#e2e8f0; border-radius:2px; overflow:hidden;">
                                <div style="width:${pct}%; height:100%; background:var(--secondary-color); border-radius:2px;"></div>
                            </div>
                        </div>
                    `;
                    horasList.appendChild(item);
                });

                // Total row
                const totalRowH = document.createElement('div');
                totalRowH.className = 'breakdown-item';
                totalRowH.style.cssText = 'border-top: 2px solid var(--border-color); margin-top:6px; padding-top:8px; font-weight:600;';
                totalRowH.innerHTML = `
                    <div class="breakdown-info"><span class="breakdown-name">Total horas semanales</span></div>
                    <span class="breakdown-stats"><strong>${totalHorasTipos}</strong> hrs</span>
                `;
                horasList.appendChild(totalRowH);

                // --- Panel 2: NRCs padre por tipo ---
                const nrcsList = document.getElementById('nrcs-padre-por-tipo-list');
                nrcsList.innerHTML = '';

                const nrcsEntries = Object.entries(data.nrcs_padre_por_tipo || {})
                    .filter(([t]) => t !== 'APM')
                    .sort((a, b) => {
                        const ia = tipoOrder.indexOf(a[0]);
                        const ib = tipoOrder.indexOf(b[0]);
                        return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
                    });

                const totalNrcsPadre = nrcsEntries.reduce((s, [, n]) => s + n, 0);

                nrcsEntries.forEach(([type, n]) => {
                    const item = document.createElement('div');
                    item.className = 'breakdown-item';
                    const name = typeNames[type] || type;
                    const pct = totalNrcsPadre > 0 ? Math.round((n / totalNrcsPadre) * 100) : 0;
                    item.innerHTML = `
                        <div class="breakdown-info" style="flex:1; min-width:0;">
                            <span class="breakdown-tag badge-type ${type.toLowerCase()}">${type}</span>
                            <span class="breakdown-name">${name}</span>
                        </div>
                        <div style="display:flex; flex-direction:column; align-items:flex-end; gap:2px; min-width:90px;">
                            <span class="breakdown-stats"><strong>${n}</strong> NRCs</span>
                            <div style="width:80px; height:4px; background:#e2e8f0; border-radius:2px; overflow:hidden;">
                                <div style="width:${pct}%; height:100%; background:var(--primary-color); border-radius:2px;"></div>
                            </div>
                        </div>
                    `;
                    nrcsList.appendChild(item);
                });

                // Total row
                const totalRowN = document.createElement('div');
                totalRowN.className = 'breakdown-item';
                totalRowN.style.cssText = 'border-top: 2px solid var(--border-color); margin-top:6px; padding-top:8px; font-weight:600;';
                totalRowN.innerHTML = `
                    <div class="breakdown-info"><span class="breakdown-name">Total asignaturas (NRC padre)</span></div>
                    <span class="breakdown-stats"><strong>${totalNrcsPadre}</strong> NRCs</span>
                `;
                nrcsList.appendChild(totalRowN);

                // --- Panel 3: Edificios ---
                const bldgList = document.getElementById('building-breakdown-list');
                bldgList.innerHTML = '';
                
                const sortedBuildings = Object.entries(data.edificios).sort((a,b) => b[1] - a[1]);
                sortedBuildings.forEach(([name, count]) => {
                    const item = document.createElement('div');
                    item.className = 'breakdown-item';
                    item.innerHTML = `
                        <div class="breakdown-info">
                            <i class="fa-solid fa-building-columns text-light" style="color: var(--secondary-color); font-size:1.1rem;"></i>
                            <span class="breakdown-name">${name}</span>
                        </div>
                        <span class="breakdown-stats">${count} bloques/sem</span>
                    `;
                    bldgList.appendChild(item);
                });

                // --- Panel 4: Contratos (Doughnut Chart) ---
                renderDoughnutChart(
                    'chart-contratos',
                    data.contratos || {},
                    [
                        '#0f2b5c', '#da291c', '#3a7fc1', '#e57c35',
                        '#4caf7d', '#9c59d1', '#64748b', '#f0a500'
                    ]
                );

                // --- Panel 5: Jerarquías (Horizontal Bar Chart) ---
                renderBarChart(
                    'chart-jerarquias',
                    data.jerarquias || {}
                );

                // --- Panel 6: Grados / Títulos (Doughnut Chart) ---
                renderDoughnutChart(
                    'chart-grados',
                    data.grados || {},
                    [
                        '#3a7fc1', '#da291c', '#0f2b5c', '#4caf7d',
                        '#e57c35', '#9c59d1', '#64748b', '#f0a500'
                    ]
                );

            }
        })
        .catch(err => console.error('Error loading dashboard summary:', err));
}

// --- TAB 2: ASIGNATURAS ---
function loadAsignaturas() {
    const url = new URL('/api/asignaturas', window.location.origin);
    if (globalFilters.carrera) url.searchParams.append('carrera', globalFilters.carrera);
    if (globalFilters.jornada) url.searchParams.append('jornada', globalFilters.jornada);
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.success && !data.empty) {
                allAsignaturas = data.asignaturas;
                // Reset advanced filters when global filters change
                asignaturaFilters.query = '';
                asignaturaFilters.tipo = '';
                asignaturaFilters.seccion = '';
                asignaturaFilters.sort = '';
                document.getElementById('search-asignatura').value = '';
                document.getElementById('filter-asignatura-tipo').value = '';
                document.getElementById('filter-asignatura-seccion').value = '';
                document.getElementById('sort-asignaturas').value = '';
                applyAsignaturaFilters();
            }
        })
        .catch(err => console.error('Error loading asignaturas:', err));
}

// Apply all client-side asignatura filters and sorting
function applyAsignaturaFilters() {
    const { query, tipo, seccion, sort } = asignaturaFilters;
    const q = query.toLowerCase().trim();
    const sec = seccion.toLowerCase().trim();

    // Flatten: parents + all children
    let flat = [];
    allAsignaturas.forEach(p => {
        flat.push({ ...p, _isChild: false, _parentNrc: null });
        if (p.componentes_hijo) {
            p.componentes_hijo.forEach(c => flat.push({ ...c, _isChild: true, _parentNrc: p.NRC }));
        }
    });

    // Filter
    flat = flat.filter(item => {
        const matchQuery = !q ||
            (item.TITULO && item.TITULO.toLowerCase().includes(q)) ||
            (item.NRC && String(item.NRC).includes(q)) ||
            (item.MATERIA && item.MATERIA.toLowerCase().includes(q)) ||
            (item.DOCENTE && item.DOCENTE.toLowerCase().includes(q)) ||
            (item.SECCION && item.SECCION.toLowerCase().includes(q));

        const matchTipo = !tipo || (item.TIPO_HORARIO && item.TIPO_HORARIO === tipo);
        const matchSeccion = !sec || (item.SECCION && item.SECCION.toLowerCase().includes(sec));

        return matchQuery && matchTipo && matchSeccion;
    });

    // Sort
    if (sort === 'nrc') {
        flat.sort((a, b) => String(a.NRC).localeCompare(String(b.NRC)));
    } else if (sort === 'titulo') {
        flat.sort((a, b) => (a.TITULO || '').localeCompare(b.TITULO || ''));
    } else if (sort === 'docente') {
        flat.sort((a, b) => (a.DOCENTE || '').localeCompare(b.DOCENTE || ''));
    } else if (sort === 'inscritos') {
        flat.sort((a, b) => (b.INSCRITOS || 0) - (a.INSCRITOS || 0));
    } else if (sort === 'disponibles') {
        flat.sort((a, b) => (b.DISPONIBLES || 0) - (a.DISPONIBLES || 0));
    } else if (sort === 'horas') {
        flat.sort((a, b) => (b.HORAS_TOTALES || 0) - (a.HORAS_TOTALES || 0));
    }

    renderFlatAsignaturasTable(flat);
}

function renderFlatAsignaturasTable(items) {
    const tbody = document.getElementById('tbody-asignaturas');
    tbody.innerHTML = '';

    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" style="padding:30px; text-align:center; color:var(--text-secondary);">No se encontraron asignaturas con los filtros seleccionados.</td></tr>';
        return;
    }

    items.forEach(item => {
        const row = document.createElement('tr');
        const typeClass = item.TIPO_HORARIO ? item.TIPO_HORARIO.toLowerCase() : '';
        const docenteName = item.DOCENTE || 'Sin docente asignado';
        const docenteLink = item.DOCENTE
            ? `<a href="#" class="docente-link" onclick="navigateToDocente('${item.DOCENTE.replace(/'/g, "\\'")}')"><i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.7rem; margin-right:4px;"></i>${item.DOCENTE}</a>`
            : 'Sin docente asignado';

        let tituloCell;
        if (item._isChild) {
            tituloCell = `<td style="padding-left:24px;"><i class="fa-solid fa-arrow-turn-up" style="transform:rotate(90deg); margin-right:8px; color:var(--text-light)"></i>${item.TITULO} <span style="font-size:0.75rem; color:var(--text-secondary);">(comp. NRC ${item._parentNrc})</span></td>`;
            row.className = 'child-row child-row-flat';
        } else {
            tituloCell = `<td><strong>${item.TITULO}</strong></td>`;
            row.className = 'parent-row';
        }

        row.innerHTML = `
            <td></td>
            <td><strong>${item.NRC}</strong></td>
            <td>${item.MATERIA || ''}${item.CURSO || ''}</td>
            ${tituloCell}
            <td>${item.SECCION || '-'}</td>
            <td>${item.NIVEL != null ? item.NIVEL : '-'}</td>
            <td>${item.HORAS_TOTALES || '0'} hrs</td>
            <td><span class="badge-type ${typeClass}">${item.TIPO_HORARIO || 'TEO'}</span></td>
            <td>${item.CUPO || '0'}</td>
            <td>${item.INSCRITOS || '0'}</td>
            <td>${item.DISPONIBLES || '0'}</td>
            <td>${docenteLink}</td>
        `;
        tbody.appendChild(row);
    });
}

function renderAsignaturasTable(asignaturas) {
    // Legacy: used on initial load; store and re-apply filters
    allAsignaturas = asignaturas;
    applyAsignaturaFilters();
}

function toggleAsignaturaChildren(parentNrc) {
    const parentRow = document.querySelector(`tr[data-nrc="${parentNrc}"]`);
    const toggleBtn = parentRow.querySelector('.btn-toggle-expand');
    const childRows = document.querySelectorAll(`.child-of-${parentNrc}`);
    
    const isExpanded = toggleBtn.classList.contains('expanded');
    
    if (isExpanded) {
        toggleBtn.classList.remove('expanded');
        childRows.forEach(row => row.style.display = 'none');
    } else {
        toggleBtn.classList.add('expanded');
        childRows.forEach(row => row.style.display = 'table-row');
    }
}

// Navigate to docentes tab and auto-select a teacher by name
function navigateToDocente(nombre) {
    // Switch to docentes tab
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    const docenteNavBtn = document.querySelector('.nav-item[data-tab="docentes"]');
    if (docenteNavBtn) docenteNavBtn.classList.add('active');

    // Mark the target name so selectDocente picks it
    const targetName = nombre.trim();

    fetch('/api/docentes')
        .then(res => res.json())
        .then(data => {
            if (data.success && !data.empty) {
                allDocentes = data.docentes;
                activeTab = 'docentes';
                hideAllTabContents();
                const tabEl = document.getElementById('tab-docentes');
                if (tabEl) tabEl.classList.add('active');

                const match = allDocentes.find(d => d.DOCENTE === targetName) || allDocentes[0];
                renderDocentesList(allDocentes);
                selectDocente(match);

                // Highlight correct item in list
                document.querySelectorAll('#list-docentes .list-item-btn').forEach(btn => {
                    if (btn.querySelector('.list-item-title')?.textContent === match.DOCENTE) {
                        btn.classList.add('selected');
                        btn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    } else {
                        btn.classList.remove('selected');
                    }
                });
            }
        })
        .catch(err => console.error('Error navigating to docente:', err));
}

// --- TAB 3: DOCENTES ---
function loadDocentes() {
    fetch('/api/docentes')
        .then(res => res.json())
        .then(data => {
            if (data.success && !data.empty) {
                allDocentes = data.docentes;
                renderDocentesList(allDocentes);
                
                // Automatically select first teacher if none selected
                if (allDocentes.length > 0) {
                    if (selectedDocente) {
                        // Check if previously selected teacher still exists
                        const exists = allDocentes.find(d => d.DOCENTE === selectedDocente.DOCENTE);
                        selectDocente(exists || allDocentes[0]);
                    } else {
                        selectDocente(allDocentes[0]);
                    }
                }
            }
        })
        .catch(err => console.error('Error loading docentes:', err));
}

function renderDocentesList(docentes) {
    const listContainer = document.getElementById('list-docentes');
    listContainer.innerHTML = '';
    
    if (docentes.length === 0) {
        listContainer.innerHTML = '<div class="text-center" style="padding:20px; color:var(--text-secondary);">No se encontraron docentes.</div>';
        return;
    }
    
    docentes.forEach(d => {
        const item = document.createElement('button');
        item.className = 'list-item-btn';
        if (selectedDocente && selectedDocente.DOCENTE === d.DOCENTE) {
            item.classList.add('selected');
        }
        
        item.innerHTML = `
            <span class="list-item-title">${d.DOCENTE}</span>
            <div class="list-item-subtitle">
                <span>Carga: ${d.total_horas} hrs</span>
                <span>${d.GRADO || 'Sin grado'}</span>
            </div>
        `;
        item.addEventListener('click', () => {
            selectDocente(d);
            // Highlight selected item in the list
            document.querySelectorAll('#list-docentes .list-item-btn').forEach(btn => btn.classList.remove('selected'));
            item.classList.add('selected');
        });
        
        listContainer.appendChild(item);
    });
}

function filterDocentesList(query) {
    const q = query.toLowerCase().trim();
    const filtered = allDocentes.filter(d => d.DOCENTE.toLowerCase().includes(q));
    renderDocentesList(filtered);
}

function selectDocente(docente) {
    selectedDocente = docente;
    
    // Populate profile card
    document.getElementById('docente-name').textContent = docente.DOCENTE;
    document.getElementById('docente-cargo').textContent = docente.CARGO || 'Docente';
    document.getElementById('docente-grado').textContent = docente.GRADO || 'N/A';
    document.getElementById('docente-id').textContent = docente.ID_DOCENTE || '-';
    document.getElementById('docente-contrato').textContent = docente.TIPO_CONTRATO || '-';
    document.getElementById('docente-jerarquia').textContent = docente.JERARQUIA || '-';
    document.getElementById('docente-sede').textContent = docente.SEDE_DOCENTE || '-';
    document.getElementById('docente-horas').textContent = docente.total_horas + ' hrs';
    document.getElementById('docente-nrc-count').textContent = docente.n_asignaturas + ' asignaturas';

    // Fetch schedule for this teacher and render timetable
    const url = new URL('/api/schedule', window.location.origin);
    url.searchParams.append('docente', docente.DOCENTE);
    if (globalFilters.carrera) url.searchParams.append('carrera', globalFilters.carrera);
    if (globalFilters.jornada) url.searchParams.append('jornada', globalFilters.jornada);
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderTimetable('docente-timetable', data.schedule, 'docente');
            }
        })
        .catch(err => console.error('Error loading schedule for docente:', err));
}

// --- TAB 4: NIVELES ---
function loadNivelSchedule(nivelStr) {
    const url = new URL('/api/schedule', window.location.origin);
    
    let displayTitle = '';
    if (nivelStr.includes('|')) {
        const [nivel, seccion] = nivelStr.split('|');
        url.searchParams.append('nivel', nivel);
        url.searchParams.append('seccion', seccion);
        displayTitle = `Horario Nivel ${nivel} - Grupo ${seccion}`;
    } else {
        url.searchParams.append('nivel', nivelStr);
        displayTitle = `Horario Nivel ${nivelStr} (Todos los Grupos)`;
    }
    
    if (globalFilters.carrera) url.searchParams.append('carrera', globalFilters.carrera);
    if (globalFilters.jornada) url.searchParams.append('jornada', globalFilters.jornada);
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const titleEl = document.getElementById('nivel-schedule-title');
                if (titleEl) {
                    titleEl.innerHTML = `<i class="fa-solid fa-calendar-days"></i> ${displayTitle}`;
                }
                document.getElementById('nivel-schedule-card').style.display = 'block';
                renderTimetable('nivel-timetable', data.schedule, 'nivel');
            }
        })
        .catch(err => console.error('Error loading schedule for nivel:', err));
}

// --- TAB 5: SALAS ---
function loadSalas() {
    fetch('/api/salas')
        .then(res => res.json())
        .then(data => {
            if (data.success && !data.empty) {
                allSalas = data.salas;
                renderSalasList(allSalas);
                
                // Automatically select first classroom
                if (allSalas.length > 0) {
                    if (selectedSala) {
                        const exists = allSalas.find(s => s.COD_SALON === selectedSala.COD_SALON);
                        selectSala(exists || allSalas[0]);
                    } else {
                        selectSala(allSalas[0]);
                    }
                }
            }
        })
        .catch(err => console.error('Error loading salas:', err));
}

function renderSalasList(salas) {
    const listContainer = document.getElementById('list-salas');
    listContainer.innerHTML = '';
    
    if (salas.length === 0) {
        listContainer.innerHTML = '<div class="text-center" style="padding:20px; color:var(--text-secondary);">No se encontraron salas.</div>';
        return;
    }
    
    salas.forEach(s => {
        const item = document.createElement('button');
        item.className = 'list-item-btn';
        if (selectedSala && selectedSala.COD_SALON === s.COD_SALON) {
            item.classList.add('selected');
        }
        
        item.innerHTML = `
            <span class="list-item-title">${s.COD_SALON}</span>
            <div class="list-item-subtitle">
                <span>Capacidad: ${s.CAPACIDAD_SALON}</span>
                <span>Edificio: ${s.COD_EDIFICIO || 'TA'}</span>
            </div>
        `;
        item.addEventListener('click', () => {
            selectSala(s);
            document.querySelectorAll('#list-salas .list-item-btn').forEach(btn => btn.classList.remove('selected'));
            item.classList.add('selected');
        });
        
        listContainer.appendChild(item);
    });
}

function filterSalasList(query) {
    const q = query.toLowerCase().trim();
    const filtered = allSalas.filter(s => s.COD_SALON.toLowerCase().includes(q) || (s.SALON && s.SALON.toLowerCase().includes(q)));
    renderSalasList(filtered);
}

function selectSala(sala) {
    selectedSala = sala;
    
    // Populate profile card
    document.getElementById('sala-name').textContent = `Sala ${sala.COD_SALON}`;
    document.getElementById('sala-edificio').textContent = sala.EDIFICIO || 'Edificio Unico';
    document.getElementById('sala-capacidad').textContent = `Capacidad: ${sala.CAPACIDAD_SALON} estudiantes`;
    document.getElementById('sala-codigo').textContent = sala.COD_SALON;
    document.getElementById('sala-ubicacion').textContent = `${sala.EDIFICIO || 'Principal'} (Código: ${sala.COD_EDIFICIO || 'TA'})`;
    document.getElementById('sala-bloques-ocupados').textContent = `${sala.ocupacion_sesiones} bloques`;

    // Fetch room schedule
    const url = new URL('/api/schedule', window.location.origin);
    url.searchParams.append('sala', sala.COD_SALON);
    if (globalFilters.carrera) url.searchParams.append('carrera', globalFilters.carrera);
    if (globalFilters.jornada) url.searchParams.append('jornada', globalFilters.jornada);
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderTimetable('sala-timetable', data.schedule, 'sala');
            }
        })
        .catch(err => console.error('Error loading schedule for sala:', err));
}

// --- TIMETABLE RENDERING ENGINE (CSS GRID) ---
function renderTimetable(containerId, scheduleData, viewType) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    const grid = document.createElement('div');
    grid.className = 'timetable-grid';
    
    // 1. Add Headers: Time Label + 5 Weekdays
    const firstHeader = document.createElement('div');
    firstHeader.className = 'grid-header grid-header-hour';
    firstHeader.textContent = 'Hora';
    grid.appendChild(firstHeader);
    
    WEEKDAYS.forEach(day => {
        const header = document.createElement('div');
        header.className = 'grid-header';
        header.textContent = day.label;
        grid.appendChild(header);
    });
    
    // 2. Generate rows for each schedule block
    SCHEDULE_BLOCKS.forEach((block, bIdx) => {
        // Add time label cell
        const hourCell = document.createElement('div');
        hourCell.className = 'grid-cell-hour';
        hourCell.innerHTML = `
            <span class="hour-title">${block.label}</span>
            <span class="hour-subtitle">${block.times}</span>
        `;
        grid.appendChild(hourCell);
        
        // Add day cells for this row
        WEEKDAYS.forEach(day => {
            const dayCell = document.createElement('div');
            dayCell.className = 'grid-cell-day';
            
            // Find matches for this day and block
            const matches = scheduleData.filter(s => {
                const isDayActive = s[day.key] === 'Y';
                return isDayActive && isSessionInBlock(s, block);
            });
            
            if (matches.length > 0) {
                dayCell.classList.add('has-class');
                
                matches.forEach((m, index) => {
                    const card = document.createElement('div');
                    
                    // Generate color based on subject name
                    const subjectName = m.TITULO || m.MATERIA || 'General';
                    let hash = 0;
                    for (let i = 0; i < subjectName.length; i++) {
                        hash = subjectName.charCodeAt(i) + ((hash << 5) - hash);
                    }
                    const hue = Math.abs(hash % 360);
                    const bgCol = `hsl(${hue}, 85%, 96%)`;
                    const borderCol = `hsl(${hue}, 70%, 45%)`;
                    
                    const typeClass = m.TIPO_HORARIO ? m.TIPO_HORARIO.toLowerCase() : 'teo';
                    
                    card.className = `schedule-block-card`;
                    card.style.setProperty('background-color', bgCol, 'important');
                    card.style.setProperty('border-left-color', borderCol, 'important');
                    
                    // Visual cascade for overlapping sections
                    if (index > 0) {
                        card.style.marginLeft = `${index * 12}px`;
                        card.style.marginTop = `-${index * 15}px`;
                        card.style.boxShadow = '-2px 2px 8px rgba(0,0,0,0.15)';
                        card.style.zIndex = index;
                    }
                    
                    // Customize meta displayed in cards based on view type
                    let metaText = '';
                    if (viewType === 'docente') {
                        // Display room and level for the teacher
                        metaText = `
                            <div class="block-meta meta-sala"><i class="fa-solid fa-door-open"></i> ${m.COD_SALON}</div>
                            <div class="block-meta meta-nivel"><i class="fa-solid fa-layer-group"></i> Nivel ${m.NIVEL}</div>
                        `;
                    } else if (viewType === 'nivel') {
                        // Display room and teacher for the level
                        metaText = `
                            <div class="block-meta meta-sala"><i class="fa-solid fa-door-open"></i> ${m.COD_SALON}</div>
                            <div class="block-meta meta-docente" title="${m.DOCENTE}"><i class="fa-solid fa-user-tie"></i> ${m.DOCENTE}</div>
                        `;
                    } else if (viewType === 'sala') {
                        // Display teacher and level for the room
                        metaText = `
                            <div class="block-meta meta-docente" title="${m.DOCENTE}"><i class="fa-solid fa-user-tie"></i> ${m.DOCENTE}</div>
                            <div class="block-meta meta-nivel"><i class="fa-solid fa-layer-group"></i> Nivel ${m.NIVEL}</div>
                        `;
                    }
                    
                    const tipoText = m.TIPO_HORARIO || 'TEO';
                    let secText = `Sec. ${m.SECCION}`;
                    if (m.subgrupo) {
                        secText = `Grupo ${m.subgrupo} (${m.SECCION})`;
                    }
                    card.innerHTML = `
                        <span class="block-subject meta-subject">${m.TITULO} <span class="block-badge-type" style="background-color: var(--text-primary); color: white;">${secText}</span> <span class="block-badge-type meta-tipo ${typeClass}">${tipoText}</span></span>
                        <span class="block-nrc-sec meta-nrc">${m.MATERIA}${m.CURSO} | NRC ${m.NRC}</span>
                        <div class="block-meta meta-time"><i class="fa-solid fa-clock"></i> ${block.times}</div>
                        ${metaText}
                    `;
                    dayCell.appendChild(card);
                });
            } else {
                // If it is room availability view, show a nice subtle "Disponible" text
                if (viewType === 'sala') {
                    const freeIndicator = document.createElement('span');
                    freeIndicator.className = 'block-free-indicator';
                    freeIndicator.textContent = 'Disponible';
                    dayCell.appendChild(freeIndicator);
                }
            }
            
            grid.appendChild(dayCell);
        });
    });
    
    container.appendChild(grid);
}

// --- CHART HELPERS ---
function renderDoughnutChart(canvasId, dataObj, colors) {
    // Destroy previous instance if exists
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
        delete chartInstances[canvasId];
    }

    const labels = Object.keys(dataObj);
    const values = Object.values(dataObj);
    if (labels.length === 0) return;

    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors || [
                    '#0f2b5c', '#da291c', '#3a7fc1', '#e57c35',
                    '#4caf7d', '#9c59d1', '#64748b', '#f0a500'
                ],
                borderColor: '#ffffff',
                borderWidth: 3,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '62%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: { family: 'Inter', size: 12 },
                        color: '#1e293b',
                        padding: 14,
                        usePointStyle: true,
                        pointStyleWidth: 10,
                        generateLabels(chart) {
                            const data = chart.data;
                            const total = data.datasets[0].data.reduce((s, v) => s + v, 0);
                            return data.labels.map((label, i) => ({
                                text: `${label}  (${data.datasets[0].data[i]})`,
                                fillStyle: data.datasets[0].backgroundColor[i],
                                strokeStyle: data.datasets[0].backgroundColor[i],
                                index: i
                            }));
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label(ctx) {
                            const total = ctx.dataset.data.reduce((s, v) => s + v, 0);
                            const pct = total > 0 ? Math.round((ctx.parsed / total) * 100) : 0;
                            return ` ${ctx.label}: ${ctx.parsed} docentes (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderBarChart(canvasId, dataObj) {
    // Destroy previous instance if exists
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
        delete chartInstances[canvasId];
    }

    // Sort descending
    const sorted = Object.entries(dataObj).sort((a, b) => b[1] - a[1]);
    const labels = sorted.map(([k]) => k);
    const values = sorted.map(([, v]) => v);
    if (labels.length === 0) return;

    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    // Generate a gradient from navy to red
    const bgColors = labels.map((_, i) => {
        const ratio = labels.length > 1 ? i / (labels.length - 1) : 0;
        const r = Math.round(15 + ratio * (218 - 15));
        const g = Math.round(43 + ratio * (41 - 43));
        const b = Math.round(92 + ratio * (28 - 92));
        return `rgba(${r},${g},${b},0.85)`;
    });

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Docentes',
                data: values,
                backgroundColor: bgColors,
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label(ctx) {
                            return ` ${ctx.parsed.x} docente${ctx.parsed.x !== 1 ? 's' : ''}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: { family: 'Inter', size: 11 },
                        color: '#64748b'
                    },
                    grid: { color: '#f1f5f9' }
                },
                y: {
                    ticks: {
                        font: { family: 'Inter', size: 11 },
                        color: '#1e293b'
                    },
                    grid: { display: false }
                }
            }
        }
    });
}

// --- TOAST NOTIFICATIONS ---
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = '<i class="fa-solid fa-circle-info"></i>';
    if (type === 'success') icon = '<i class="fa-solid fa-circle-check"></i>';
    if (type === 'error') icon = '<i class="fa-solid fa-circle-exclamation"></i>';
    
    toast.innerHTML = `
        ${icon}
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 50);
    
    // Auto-dismiss
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- PDF EXPORT ---
function exportPDF(type) {
    const prevTitle = document.title;

    // Build a descriptive print title
    if (type === 'docente' && selectedDocente) {
        document.title = `Horario Docente - ${selectedDocente.DOCENTE}`;
    } else if (type === 'nivel' && selectedNivel) {
        document.title = `Horario Nivel ${selectedNivel}`;
    } else if (type === 'sala' && selectedSala) {
        document.title = `Disponibilidad Sala ${selectedSala.COD_SALON}`;
    } else if (type === 'asignaturas') {
        document.title = 'Listado de Asignaturas';
    }

    // Mark which section to print
    document.body.setAttribute('data-print-section', type);

    window.print();

    // Restore after print dialog closes
    setTimeout(() => {
        document.title = prevTitle;
        document.body.removeAttribute('data-print-section');
    }, 1000);
}

// Global functions for inline HTML event binding
window.toggleAsignaturaChildren = toggleAsignaturaChildren;
window.navigateToDocente = navigateToDocente;

// --- EXPORT ALL NIVELES PDF LOGIC ---
async function exportAllNivelesPDF() {
    const printContainer = document.getElementById('print-all-niveles');
    printContainer.innerHTML = '';
    
    // Obtain all possible level values from the dropdown
    const selectNivel = document.getElementById('select-nivel');
    const options = Array.from(selectNivel.options).map(opt => opt.value).filter(val => val !== '');
    
    if (options.length === 0) {
        showToast('No hay niveles disponibles para exportar', 'error');
        return;
    }
    
    showToast(`Generando PDF para ${options.length} niveles... por favor espere.`, 'success');
    
    for (const nivel of options) {
        const url = new URL('/api/schedule', window.location.origin);
        url.searchParams.append('nivel', nivel);
        if (globalFilters.carrera) url.searchParams.append('carrera', globalFilters.carrera);
        if (globalFilters.jornada) url.searchParams.append('jornada', globalFilters.jornada);
        
        try {
            const res = await fetch(url);
            const data = await res.json();
            
            if (data.success) {
                // Create a page container for this level
                const pageDiv = document.createElement('div');
                pageDiv.className = 'nivel-print-page';
                
                // Add header title for this level
                const header = document.createElement('h3');
                header.innerHTML = `<i class="fa-solid fa-layer-group"></i> Horario Nivel ${nivel}`;
                header.style.color = '#0f2b5c';
                header.style.marginBottom = '15px';
                pageDiv.appendChild(header);
                
                // Create a div to act as the timetable container
                const ttDiv = document.createElement('div');
                const ttId = `print-timetable-nivel-${nivel.replace(/\s+/g, '-')}`;
                ttDiv.id = ttId;
                pageDiv.appendChild(ttDiv);
                
                printContainer.appendChild(pageDiv);
                
                // Render timetable specifically in this container
                renderTimetable(ttId, data.schedule, 'nivel');
            }
        } catch (err) {
            console.error(`Error fetching schedule for nivel ${nivel}:`, err);
        }
    }
    
    // Trigger print dialog scoped to the all-niveles section
    setTimeout(() => {
        document.body.setAttribute('data-print-section', 'all-niveles');
        window.print();
        
        // Remove attribute after print dialog closes
        setTimeout(() => {
            document.body.removeAttribute('data-print-section');
            printContainer.innerHTML = ''; // Clean up
        }, 1000);
    }, 1500);
}

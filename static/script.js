// --- STATE MANAGEMENT ---
let activeTab = 'dashboard';
let dataLoaded = false;
let globalFilters = {
    carrera: '',
    jornada: ''
};

let allDocentes = [];
let allSalas = [];
let selectedDocente = null;
let selectedSala = null;
let selectedNivel = '';

// Standard schedule blocks:
const SCHEDULE_BLOCKS = [
    { label: 'Bloque 1', times: '08:00 - 09:20', range: [800, 920] },
    { label: 'Bloque 2', times: '09:30 - 10:50', range: [930, 1050] },
    { label: 'Bloque 3', times: '11:00 - 12:20', range: [1100, 1220] },
    { label: 'Bloque 4', times: '12:30 - 13:50', range: [1230, 1350] },
    { label: 'Bloque 5', times: '14:00 - 15:20', range: [1400, 1520] },
    { label: 'Bloque 6', times: '15:30 - 16:50', range: [1530, 1650] },
    { label: 'Bloque 7', times: '17:00 - 18:20', range: [1700, 1820] },
    { label: 'Bloque 8', times: '18:30 - 19:50', range: [1830, 1950] }
];

const WEEKDAYS = [
    { key: 'LUNES', label: 'Lunes' },
    { key: 'MARTES', label: 'Martes' },
    { key: 'MIERCOLES', label: 'Miércoles' },
    { key: 'JUEVES', label: 'Jueves' },
    { key: 'VIERNES', label: 'Viernes' }
];

// Helper to determine block index by HORA_INCIO
function getBlockIndex(horaInicioStr) {
    if (!horaInicioStr) return -1;
    const h = parseInt(horaInicioStr);
    
    // We check which standard range the start time fits into
    if (h >= 800 && h < 930) return 0;
    if (h >= 930 && h < 1100) return 1;
    if (h >= 1100 && h < 1230) return 2;
    if (h >= 1230 && h < 1400) return 3;
    if (h >= 1400 && h < 1530) return 4;
    if (h >= 1530 && h < 1700) return 5;
    if (h >= 1700 && h < 1830) return 6;
    if (h >= 1830) return 7;
    return -1;
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
            const file = fileInput.files[0];
            fileNameDisplay.textContent = file.name;
            uploadCSV(file);
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
        const files = dt.files;
        if (files.length > 0 && files[0].name.endsWith('.csv')) {
            fileInput.files = files;
            fileNameDisplay.textContent = files[0].name;
            uploadCSV(files[0]);
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
        filterAsignaturasTable(e.target.value);
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
}

// --- FILE UPLOAD LOGIC ---
function uploadCSV(file) {
    const uploadProgress = document.getElementById('upload-progress');
    const progressBarFill = uploadProgress.querySelector('.progress-bar-fill');
    
    uploadProgress.style.display = 'block';
    progressBarFill.style.width = '0%';
    
    const formData = new FormData();
    formData.append('file', file);
    
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
                data.niveles.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n;
                    opt.textContent = `Nivel ${n} (Semestre ${n / 10})`;
                    selectNivel.appendChild(opt);
                });
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

                // Render component type breakdown
                const compList = document.getElementById('component-breakdown-list');
                compList.innerHTML = '';
                
                const typeNames = {
                    'TEO': 'Teoría / Cátedra',
                    'AYU': 'Ayudantía',
                    'LAB': 'Laboratorio',
                    'APM': 'Autoaprendizaje / Plataforma',
                    'TER': 'Terreno'
                };
                
                // Sort breakdown items descending by count
                const sortedComponents = Object.entries(data.components).sort((a,b) => b[1] - a[1]);
                sortedComponents.forEach(([type, count]) => {
                    const item = document.createElement('div');
                    item.className = 'breakdown-item';
                    
                    const name = typeNames[type] || type;
                    const badgeClass = type.toLowerCase();
                    
                    item.innerHTML = `
                        <div class="breakdown-info">
                            <span class="breakdown-tag badge-type ${badgeClass}">${type}</span>
                            <span class="breakdown-name">${name}</span>
                        </div>
                        <span class="breakdown-stats">${count} secciones</span>
                    `;
                    compList.appendChild(item);
                });

                // Render building breakdown
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
                renderAsignaturasTable(data.asignaturas);
            }
        })
        .catch(err => console.error('Error loading asignaturas:', err));
}

function renderAsignaturasTable(asignaturas) {
    const tbody = document.getElementById('tbody-asignaturas');
    tbody.innerHTML = '';
    
    if (asignaturas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="text-center" style="padding:30px; text-align:center;">No se encontraron asignaturas con los filtros seleccionados.</td></tr>';
        return;
    }
    
    asignaturas.forEach(p => {
        const hasChildren = p.componentes_hijo && p.componentes_hijo.length > 0;
        const row = document.createElement('tr');
        row.className = 'parent-row';
        row.setAttribute('data-nrc', p.NRC);
        
        const typeClass = p.TIPO_HORARIO ? p.TIPO_HORARIO.toLowerCase() : '';
        const docenteName = p.DOCENTE || 'Sin docente asignado';
        const expandBtn = hasChildren 
            ? `<button class="btn-toggle-expand" onclick="toggleAsignaturaChildren('${p.NRC}')"><i class="fa-solid fa-chevron-right"></i></button>`
            : '';
            
        row.innerHTML = `
            <td>${expandBtn}</td>
            <td><strong>${p.NRC}</strong></td>
            <td>${p.MATERIA}${p.CURSO}</td>
            <td>${p.TITULO}</td>
            <td>${p.SECCION || '-'}</td>
            <td>${p.HORAS_TOTALES || '0'} hrs</td>
            <td><span class="badge-type ${typeClass}">${p.TIPO_HORARIO || 'TEO'}</span></td>
            <td>${p.CUPO || '0'}</td>
            <td>${p.INSCRITOS || '0'}</td>
            <td>${p.DISPONIBLES || '0'}</td>
            <td>${docenteName}</td>
        `;
        tbody.appendChild(row);
        
        // Append children rows immediately, but hidden
        if (hasChildren) {
            p.componentes_hijo.forEach(c => {
                const childRow = document.createElement('tr');
                childRow.className = `child-row child-of-${p.NRC}`;
                childRow.style.display = 'none'; // Hidden initially
                
                const cTypeClass = c.TIPO_HORARIO ? c.TIPO_HORARIO.toLowerCase() : '';
                const cDocenteName = c.DOCENTE || 'Sin docente asignado';
                
                childRow.innerHTML = `
                    <td></td>
                    <td>${c.NRC}</td>
                    <td>${c.MATERIA}${c.CURSO}</td>
                    <td style="padding-left: 24px;"><i class="fa-solid fa-arrow-turn-up" style="transform: rotate(90deg); margin-right: 8px; color: var(--text-light)"></i> ${c.TITULO} (Hijo de NRC ${p.NRC})</td>
                    <td>${c.SECCION || '-'}</td>
                    <td>${c.HORAS_TOTALES || '0'} hrs</td>
                    <td><span class="badge-type ${cTypeClass}">${c.TIPO_HORARIO || 'AYU'}</span></td>
                    <td>${c.CUPO || '0'}</td>
                    <td>${c.INSCRITOS || '0'}</td>
                    <td>${c.DISPONIBLES || '0'}</td>
                    <td>${cDocenteName}</td>
                `;
                tbody.appendChild(childRow);
            });
        }
    });
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

// Client side filtering for table
function filterAsignaturasTable(query) {
    const q = query.toLowerCase().trim();
    const rows = document.querySelectorAll('#tbody-asignaturas tr');
    
    if (!q) {
        // Show only parents, hide all children and reset expand buttons
        rows.forEach(row => {
            if (row.classList.contains('parent-row')) {
                row.style.display = 'table-row';
                const btn = row.querySelector('.btn-toggle-expand');
                if (btn) btn.classList.remove('expanded');
            } else if (row.classList.contains('child-row')) {
                row.style.display = 'none';
            }
        });
        return;
    }
    
    // If searching, we display both matching parents AND matching children directly.
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(q)) {
            row.style.display = 'table-row';
        } else {
            row.style.display = 'none';
        }
    });
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
function loadNivelSchedule(nivel) {
    const url = new URL('/api/schedule', window.location.origin);
    url.searchParams.append('nivel', nivel);
    if (globalFilters.carrera) url.searchParams.append('carrera', globalFilters.carrera);
    if (globalFilters.jornada) url.searchParams.append('jornada', globalFilters.jornada);
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
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
            
            // Find matches for this day and block index
            const matches = scheduleData.filter(s => {
                const isDayActive = s[day.key] === 'Y';
                const sBlockIdx = getBlockIndex(s.HORA_INCIO);
                return isDayActive && sBlockIdx === bIdx;
            });
            
            if (matches.length > 0) {
                dayCell.classList.add('has-class');
                
                matches.forEach(m => {
                    const card = document.createElement('div');
                    const typeClass = m.TIPO_HORARIO ? m.TIPO_HORARIO.toLowerCase() : 'teo';
                    card.className = `schedule-block-card type-${typeClass}`;
                    
                    // Customize meta displayed in cards based on view type
                    let metaText = '';
                    if (viewType === 'docente') {
                        // Display room and level for the teacher
                        metaText = `
                            <div class="block-meta"><i class="fa-solid fa-door-open"></i> ${m.COD_SALON}</div>
                            <div class="block-meta"><i class="fa-solid fa-layer-group"></i> Nivel ${m.NIVEL}</div>
                        `;
                    } else if (viewType === 'nivel') {
                        // Display room and teacher for the level
                        metaText = `
                            <div class="block-meta"><i class="fa-solid fa-door-open"></i> ${m.COD_SALON}</div>
                            <div class="block-meta" title="${m.DOCENTE}"><i class="fa-solid fa-user-tie"></i> ${m.DOCENTE}</div>
                        `;
                    } else if (viewType === 'sala') {
                        // Display teacher and level for the room
                        metaText = `
                            <div class="block-meta" title="${m.DOCENTE}"><i class="fa-solid fa-user-tie"></i> ${m.DOCENTE}</div>
                            <div class="block-meta"><i class="fa-solid fa-layer-group"></i> Nivel ${m.NIVEL}</div>
                        `;
                    }
                    
                    card.innerHTML = `
                        <span class="block-subject">${m.TITULO}</span>
                        <span class="block-nrc-sec">${m.MATERIA}${m.CURSO} [Sec. ${m.SECCION}] | NRC ${m.NRC}</span>
                        <div class="block-meta"><i class="fa-solid fa-clock"></i> ${m.hora_inicio_fmt} - ${m.hora_fin_fmt}</div>
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

// Global functions for inline HTML event binding
window.toggleAsignaturaChildren = toggleAsignaturaChildren;

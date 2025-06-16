/**
 * Scripts para la aplicación de nóminas
 */

// Detectar prefijo automáticamente basándose en la URL actual
function getUrlPrefix() {
    const path = window.location.pathname;
    if (path.startsWith('/south/')) {
        return '/south';
    }
    return '';
}

// Función para mostrar detalles de un concepto de nómina
function showDetailModal(conceptoId, mes, anio) {
    const prefix = getUrlPrefix();
    // Hacer una solicitud AJAX para obtener los detalles del concepto
    fetch(`${prefix}/api/detalle_concepto/${conceptoId}/${mes}/${anio}`)
        .then(response => response.json())
        .then(data => {
            const modal = document.getElementById('detalleModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalContent = document.getElementById('modalContent');
            
            modalTitle.textContent = data.concepto;
            
            let contentHTML = '<div class="calendar-grid">';
            // Generar encabezados de la semana
            const diasSemana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
            diasSemana.forEach(dia => {
                contentHTML += `<div style="text-align:center; font-weight:bold;">${dia}</div>`;
            });
            
            // Generar días del mes para mostrar detalles
            const startDate = new Date(anio, mes-1, 1);
            const endDate = new Date(anio, mes, 0);
            
            // Ajustar para que empiece en lunes
            const firstDay = startDate.getDay() || 7; // Convierte 0 (domingo) a 7
            const daysToAdd = (firstDay - 1) % 7;
            
            // Añadir celdas vacías para los días anteriores al mes
            for (let i = 0; i < daysToAdd; i++) {
                contentHTML += '<div class="day-square" style="background-color: #f5f5f5;"></div>';
            }
            
            // Añadir los días del mes
            for (let day = 1; day <= endDate.getDate(); day++) {
                const currentDate = new Date(anio, mes-1, day);
                const dateStr = `${anio}-${String(mes).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                
                let classNames = "day-square";
                let dayContent = day;
                
                // Comprobar si este día tiene el plus
                if (data.dias.includes(dateStr)) {
                    classNames += " plus-day";
                    dayContent += `<br><span style="font-size:0.8em;">${data.valor} €</span>`;
                }
                
                contentHTML += `<div class="${classNames}" style="background-color: ${data.dias.includes(dateStr) ? '#e6ffe6' : '#f5f5f5'}">${dayContent}</div>`;
            }
            
            contentHTML += '</div>';
            contentHTML += `<p>Total: ${data.total.toFixed(2)} €</p>`;
            
            modalContent.innerHTML = contentHTML;
            modal.style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ha ocurrido un error al cargar los detalles');
        });
}

// Función para cerrar el modal
function closeModal() {
    document.getElementById('detalleModal').style.display = 'none';
}

// Cerrar el modal si se hace clic fuera de él
window.onclick = function(event) {
    const modal = document.getElementById('detalleModal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}

// Función para añadir un turno en el simulador
function addShift() {
    const container = document.getElementById('shifts-container');
    const index = container.children.length + 1;
    if(index > 3) return;
    let html = `
    <div class="day-square">
        <h4>Turno ${index}</h4>
        <label>Hora Inicio:
            <input type="time" name="start_time_${index}" required>
        </label>
        <label>Hora Fin:
            <input type="time" name="end_time_${index}" required>
        </label>
    </div>`;
    container.insertAdjacentHTML('beforeend', html);
}

// Añadir primer turno automáticamente al cargar la página del simulador
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('shifts-container')) {
        addShift();
    }
});

/**
 * Verifica el estado de sincronización y actualiza la interfaz
 */
function checkSyncStatus() {
    const prefix = getUrlPrefix();
    fetch(`${prefix}/sincronizacion/estado`)
        .then(response => response.json())
        .then(data => {
            const syncIndicator = document.getElementById('sync-indicator');
            
            if (syncIndicator) {
                if (data.en_progreso) {
                    syncIndicator.innerHTML = '<div class="spinner-small"></div> Sincronizando turnos...';
                    syncIndicator.className = 'sync-status in-progress';
                    
                    // Verificar de nuevo en 5 segundos
                    setTimeout(checkSyncStatus, 5000);
                } else {
                    if (data.ultima_sincronizacion) {
                        const fecha = new Date(data.ultima_sincronizacion);
                        syncIndicator.innerHTML = 'Última sincronización: ' + fecha.toLocaleString();
                        syncIndicator.className = 'sync-status complete';
                        
                        // Si la sincronización recién terminó, recargar la página
                        if (data.recien_completado) {
                            location.reload();
                        }
                    } else {
                        syncIndicator.innerHTML = 'No se ha sincronizado';
                        syncIndicator.className = 'sync-status none';
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error verificando estado de sincronización:', error);
        });
}

// Iniciar verificación de estado cuando existe el indicador
document.addEventListener('DOMContentLoaded', function() {
    const syncIndicator = document.getElementById('sync-indicator');
    if (syncIndicator) {
        checkSyncStatus();
    }
});

/**
 * Añade un indicador de desplazamiento en dispositivos móviles
 */
function addSwipeIndicator() {
    // Solo para dispositivos táctiles
    if (window.matchMedia('(hover: none)').matches) {
        const calendarContainers = document.querySelectorAll('.calendar-container');
        
        calendarContainers.forEach(container => {
            // Verificar si el container necesita scroll
            if (container.scrollWidth > container.clientWidth) {
                // Añadir indicador solo si no existe ya
                if (!container.querySelector('.swipe-indicator')) {
                    const indicator = document.createElement('div');
                    indicator.className = 'swipe-indicator';
                    container.appendChild(indicator);
                    
                    // Ocultar el indicador después de que el usuario haga scroll
                    container.addEventListener('scroll', function() {
                        indicator.style.opacity = '0';
                        indicator.style.transition = 'opacity 0.5s';
                        
                        // Eliminar después de la transición
                        setTimeout(() => {
                            if (indicator.parentNode) {
                                indicator.parentNode.removeChild(indicator);
                            }
                        }, 500);
                    }, { once: true });
                }
            }
        });
    }
}

// Ejecutar después de que el DOM esté cargado
document.addEventListener('DOMContentLoaded', function() {
    // Verificar estado de sincronización
    const syncIndicator = document.getElementById('sync-indicator');
    if (syncIndicator) {
        checkSyncStatus();
    }
    
    // Añadir indicador de desplazamiento
    addSwipeIndicator();
});

// Añadir a web/static/scripts.js

/**
 * Añade elementos fijos para indicar scroll lateral
 */
/**
 * Añade indicador de desplazamiento en dispositivos móviles (solo el icono, sin difuminado)
 */
function addScrollIndicators() {
    // Solo para dispositivos táctiles
    if (window.matchMedia('(hover: none)').matches) {
        const calendarContainers = document.querySelectorAll('.calendar-container');
        
        calendarContainers.forEach(container => {
            // Verificar si el container necesita scroll
            if (container.scrollWidth > container.clientWidth) {
                // Añadir indicador solo si no existe ya
                if (!container.querySelector('.swipe-indicator')) {
                    const indicator = document.createElement('div');
                    indicator.className = 'swipe-indicator';
                    container.appendChild(indicator);
                    
                    // Ocultar el indicador después de que el usuario haga scroll
                    container.addEventListener('scroll', function() {
                        indicator.style.opacity = '0';
                        indicator.style.transition = 'opacity 0.5s';
                        
                        // Eliminar después de la transición
                        setTimeout(() => {
                            if (indicator.parentNode) {
                                indicator.parentNode.removeChild(indicator);
                            }
                        }, 500);
                    }, { once: true });
                }
            }
        });
    }
}

/**
 * Verifica el estado de sincronización y actualiza la interfaz
 * con manejo de errores mejorado
 */
function checkSyncStatus() {
    const prefix = getUrlPrefix();
    fetch(`${prefix}/sincronizacion/estado`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Error en la respuesta del servidor');
            }
            return response.json();
        })
        .then(data => {
            const syncIndicator = document.getElementById('sync-indicator');
            const syncNotification = document.getElementById('sync-notification');
            const syncNotificationMessage = document.getElementById('sync-notification-message');
            
            if (syncIndicator) {
                if (data.error) {
                    // Hubo un error al consultar el estado
                    syncIndicator.innerHTML = 'Error al verificar estado';
                    syncIndicator.className = 'sync-status error';
                    
                    if (syncNotification && syncNotificationMessage) {
                        syncNotificationMessage.textContent = 'No se pudo verificar el estado de sincronización. Puede haber un problema con la conexión al servidor.';
                        syncNotification.style.display = 'block';
                    }
                    
                    // Reintentar en 10 segundos
                    setTimeout(checkSyncStatus, 10000);
                    return;
                }
                
                if (data.en_progreso) {
                    syncIndicator.innerHTML = '<div class="spinner-small"></div> Sincronizando turnos...';
                    syncIndicator.className = 'sync-status in-progress';
                    
                    // Ocultar notificación si estaba visible
                    if (syncNotification) {
                        syncNotification.style.display = 'none';
                    }
                    
                    // Verificar de nuevo en 5 segundos
                    setTimeout(checkSyncStatus, 5000);
                } else {
                    if (data.ultima_sincronizacion) {
                        const fecha = new Date(data.ultima_sincronizacion);
                        syncIndicator.innerHTML = 'Última sincronización: ' + fecha.toLocaleString();
                        syncIndicator.className = 'sync-status complete';
                        
                        // Si la sincronización recién terminó, recargar la página
                        if (data.recien_completado) {
                            location.reload();
                        }
                    } else {
                        syncIndicator.innerHTML = 'No se ha sincronizado';
                        syncIndicator.className = 'sync-status none';
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error verificando estado de sincronización:', error);
            
            // Actualizar la UI para indicar el error
            const syncIndicator = document.getElementById('sync-indicator');
            const syncNotification = document.getElementById('sync-notification');
            const syncNotificationMessage = document.getElementById('sync-notification-message');
            
            if (syncIndicator) {
                syncIndicator.innerHTML = 'Error de conexión';
                syncIndicator.className = 'sync-status error';
            }
            
            if (syncNotification && syncNotificationMessage) {
                syncNotificationMessage.textContent = 'Error al conectar con el servidor. Por favor, verifica tu conexión a internet.';
                syncNotification.style.display = 'block';
            }
            
            // Reintentar en 10 segundos
            setTimeout(checkSyncStatus, 10000);
        });
}

/**
 * Muestra una notificación de error de sincronización
 */
function showSyncError(message) {
    const syncNotification = document.getElementById('sync-notification');
    const syncNotificationMessage = document.getElementById('sync-notification-message');
    
    if (syncNotification && syncNotificationMessage) {
        syncNotificationMessage.textContent = message;
        syncNotification.style.display = 'block';
    }
}

/**
 * Obtiene el último error de sincronización y lo muestra si es necesario
 */
function checkSyncError() {
    const prefix = getUrlPrefix();
    fetch(`${prefix}/sincronizacion/ultimo-error`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Error en la respuesta del servidor');
            }
            return response.json();
        })
        .then(data => {
            if (data.hay_error && data.mensaje_error) {
                showSyncError(data.mensaje_error);
            }
        })
        .catch(error => {
            console.error('Error al verificar errores de sincronización:', error);
        });
}

// Modificar onDOMReady para incluir verificación de errores
document.addEventListener('DOMContentLoaded', function() {
    // Verificar estado de sincronización
    const syncIndicator = document.getElementById('sync-indicator');
    if (syncIndicator) {
        if (typeof checkSyncStatus === 'function') {
            checkSyncStatus();
        }
        
        // Verificar si hay errores guardados
        if (typeof checkSyncError === 'function') {
            checkSyncError();
        }
    }
    
    // Añadir indicadores de scroll
    if (typeof addScrollIndicators === 'function') {
        addScrollIndicators();
    }
});
/**
 * Scripts para la aplicación de nóminas
 */

// Función para mostrar detalles de un concepto de nómina
function showDetailModal(conceptoId, mes, anio) {
    // Hacer una solicitud AJAX para obtener los detalles del concepto
    fetch(`/api/detalle_concepto/${conceptoId}/${mes}/${anio}`)
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
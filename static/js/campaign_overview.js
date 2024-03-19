document.addEventListener("DOMContentLoaded", function() {
    // Ссылки на ваши изображения
    const editIcon = '<img src="static/images/edit.png" alt="Edit">';
    const saveIcon = '<img src="static/images/save.png" alt="Save">';
    const deleteIcon = '<img src="static/images/delete.png" alt="Delete">';

    // Обработчик нажатия на кнопку сохранения изменений
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            const row = this.closest('tr');
            const deleteBtn = row.querySelector('.delete-btn');

            if (row.classList.contains('editing')) {
                // В режиме редактирования
                const confirmSave = confirm("Save changes?");
                if (confirmSave) {
                    // Проверяем, заполнены ли все поля
                    const inputs = row.querySelectorAll('td:not(:last-child)');
                    let allFieldsFilled = true;
                    inputs.forEach(input => {
                        if (input.innerText.trim() === '') {
                            allFieldsFilled = false;
                        }
                    });

                    if (allFieldsFilled) {
                        const id = row.id.split('-')[1];
                        const data = {
                            url: row.cells[0].innerText,
                            campaign_content: row.cells[1].innerText,
                            campaign_source: row.cells[2].innerText,
                            campaign_medium: row.cells[3].innerText,
                            short_secure_url: row.cells[4].innerText,
                            clicks_count: row.cells[5].innerText,
                        };

                        fetch(`/edit-row/${id}`, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(data)
                        })
                        .then(response => response.json())
                        .then(result => {
                            alert(result.message);
                            if (result.status === 'success') {
                                Array.from(row.cells).forEach(cell => cell.contentEditable = false);
                                row.classList.remove('editing');
                                button.innerHTML = editIcon; // Вернуть значок редактирования
                                deleteBtn.innerHTML = deleteIcon; // Вернуть значок удаления
                            }
                        })
                        .catch(error => console.error('Error:', error));
                    } else {
                        alert('Please fill in all fields before saving.');
                    }
                }
            } else {
                // Вход в режим редактирования
                Array.from(row.cells).forEach((cell, index) => {
                    if (index < row.cells.length - 6) {
                        cell.dataset.originalValue = cell.innerText;
                        cell.contentEditable = true;
                    }
                });
                row.classList.add('editing');
                this.innerHTML = saveIcon; // Задать значок сохранения
                deleteBtn.innerHTML = '<img src="static/images/cancel.png" alt="Cancel">'; // Задать значок отмены
            }
        });
    });

    // Обработчик нажатия на кнопку удаления
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const row = this.closest('tr');
            if (row.classList.contains('editing')) {
                // Если мы в режиме редактирования, просто выходим из него
                Array.from(row.cells).forEach(cell => cell.contentEditable = false);
                row.classList.remove('editing');
                const editBtn = row.querySelector('.edit-btn');
                editBtn.innerHTML = editIcon; // Вернуть значок редактирования
                this.innerHTML = deleteIcon;
                // Восстанавливаем изначальные значения
                Array.from(row.cells).forEach((cell, index) => {
                    if (index < row.cells.length - 6) {
                        cell.innerText = cell.dataset.originalValue;
                    }
                });
            } else {
                const id = row.id.split('-')[1];
                const confirmDelete = confirm("Are you sure you want to delete this row?");
                if (confirmDelete) {
                    fetch(`/delete-row/${id}`, {
                        method: 'POST',
                    })
                    .then(response => response.json())
                    .then(result => {
                        alert(result.message);
                        if (result.status === 'success') {
                            row.remove();
                        }
                    })
                    .catch(error => console.error('Error:', error));
                }
            }
        });
    });
});

document.addEventListener("DOMContentLoaded", function() {
    // Add click event listeners to all copy buttons
    document.querySelectorAll('.table-container .copy-btn').forEach(button => {
        button.addEventListener('click', function() {
            // Find the closest table-container parent and select the table
            const table = this.closest('.table-container').querySelector('table');
            let tableContent = '';

            // Loop through each row and collect the data
            Array.from(table.rows).forEach((row) => {
                // Check if the row is a 'Total Clicks' row
                if (row.classList.contains('total-clicks')) {
                    // Append the 'Total Clicks' text once followed by three tabs and then the total click counts
                    tableContent += 'Total Clicks' + '\t'.repeat(4) + // One for 'Total Clicks' and three extra
                                    row.cells[row.cells.length - 5].innerText.trim() + '\t' +
                                    row.cells[row.cells.length - 4].innerText.trim() + '\t' +
                                    row.cells[row.cells.length - 3].innerText.trim() + '\t' +
                                    row.cells[row.cells.length - 2].innerText.trim() + '\t' +
                                    row.cells[row.cells.length - 1].innerText.trim() + '\n';
                } else {
                    // For all other rows, copy all cells except the last one (Actions)
                    let rowData = Array.from(row.cells).slice(0, -1)
                                    .map(cell => cell.innerText.trim()) // Trim the cell text
                                    .join('\t'); // Separate cells with a tab character
                    tableContent += rowData + '\n'; // Add a newline after each row
                }
            });

            // Attempt to copy the collected data to the clipboard
            navigator.clipboard.writeText(tableContent.trim()).then(() => {
                alert('Table content copied to clipboard.');
            }).catch(err => {
                console.error('Error copying table content:', err);
                alert('Error copying table content. Please try again.');
            });
        });
    });
});


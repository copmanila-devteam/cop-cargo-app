import {Application, Controller} from'./stimulus.js'


const app = Application.start();

const $ = window.$;

class Attendees extends Controller{

    static targets = ["table", 'attendeeForm', 'formMessages', 'copiderrors', 'firstnameerrors', 'middlenameerrors', 'lastnameerrors', 'mobileContainer']
    static values = {

        entriesUrl: String,
    }


    connect(){

        this.getAttendees()
    }

    _getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    

    resetForm(){

        this.attendeeFormTarget.reset()
    }


    async addAttendee(e){
        e.preventDefault()

        const formData = {
            cop_id: $('#id_cop_id').val() ,
            first_name: $('#id_first_name').val(),
            middle_name: $('#id_middle_name').val(),
            last_name: $('#id_last_name').val(),
        }
        
       
        try{
            const response = await fetch(this.entriesUrlValue, {
                method: 'POST',
                headers: {
                    'Content-Type':'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this._getCSRFToken(),
                },
                body: JSON.stringify(formData)

            });

            const data = await response.json();

            if (data['Status'] == 'Success'){
                console.log(data['message'])
                console.log("Target found:", this.formMessagesTarget);
                this.getAttendees();
                this.resetForm();
                $(this.formMessagesTarget).append(`<div class="col-12" id="success-message">
                                   <div class="alert alert-success" role="alert">
                                        ${data['message']}
                                    </div>
                                </div>`);
                setTimeout(() => $("#success-message").fadeOut(), 1000)
               

            }
            else if (data['Status'] == 'Error Fields'){
                console.log(data['message'])

                const errorFields = data['message']
                if (errorFields && errorFields['cop_id']){
                    $(this.copiderrorsTarget).empty();
                    
                    errorFields['cop_id'].forEach((data, i) => {
                        $(this.copiderrorsTarget).append(`<li style="color:red">${data['message']}</li>`)
                    });
                    setTimeout(()=>  $(this.copiderrorsTarget).empty() ,1000)
                }

                if (errorFields && errorFields['first_name']){
                    $(this.firstnameerrorsTarget).empty()

                    errorFields['first_name'].forEach((data, i) => {
                        $(this.firstnameerrorsTarget).append(`<li style="color:red">${data['message']}</li>`)
                    });
                    setTimeout(()=>  $(this.firstnameerrorsTarget).empty() ,1000)
                }

                if (errorFields && errorFields['middle_name']){
                     $(this.middlenameerrorsTarget).empty()
                    errorFields['middle_name'].forEach((data, i) => {
                        $(this.middlenameerrorsTarget).append(`<li style="color:red">${data['message']}</li>`)
                    });
                    setTimeout(()=>  $(this.middlenameerrorsTarget).empty() ,1000)
                }

                if (errorFields && errorFields['last_name']){
                    $(this.lastnameerrorsTarget).empty()
                    errorFields['last_name'].forEach((data, i) => {
                        $(this.lastnameerrorsTarget).append(`<li style="color:red">${data['message']}</li>`)
                    });
                    setTimeout(()=>  $(this.lastnameerrorsTarget).empty() ,1000)
                }
            }
            else if (data['Status'] == 'Error'){
                

                 $(this.formMessagesTarget).append(`<div class="col-12" id="success-message">
                                   <div class="alert alert-danger" role="alert">
                                        ${data['message']}
                                    </div>
                                </div>`);
                setTimeout(() => $("#success-message").fadeOut(), 1000)

            }
           
        }
        catch(error){
            console.log(error)

        }

    }





    async deleteAttendee(e){
        e.preventDefault()
        const id = e.currentTarget.dataset.id;

        try{

            const response = await fetch(`/attendees/${id}/delete/`,{
                method:"DELETE",
                headers:{
                    'Content-Type': 'application/json',
                    'X-Requested-With':'XMLHttpRequest',
                    'X-CSRFToken': this._getCSRFToken(),
                    
                }
            });

            if (response.ok) {
                    this.getAttendees(); // Refresh the cards/table
                }

            const data = await response.json()

            if (data['Status'] == 'Success'){

                console.log(data['message'])
            }
            else if (data['Status'] == 'Error'){

                console.log(data['message'])
            }


        }catch(error){

            console.log(error)
        }


    }

    async getAttendees(){

        try{
            const response = await fetch(this.entriesUrlValue, {
                method: 'GET',
                headers: {
                    'Content-Type':'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Cache-Control': 'no-cache',
                }

            });

            const data = await response.json()

            if (data['Status'] == 'Success'){
                if ($.fn.DataTable.isDataTable(this.tableTarget)){
                    $(this.tableTarget).DataTable().clear().destroy();
                }
                $(this.mobileContainerTarget).empty()

                if (data['data_entries'].length !== 0){

                  

                    $(this.tableTarget).DataTable({
                        data: data['data_entries'],
                        paging:true,
                        searching: true,
                        info: true,
                        columns: [
                            {data: 'cop_id'},
                            {data: 'first_name'},
                            {data: 'middle_name'},
                            {data: 'last_name'},
                            {data: 'id',
                            render:(data) => `<a class="btn btn-danger" data-id=${data} data-action="click->attendees#deleteAttendee" href="#">Delete</a>`
                            }
                        ]

                    })

                    

                    if (data['data_entries'] && data['data_entries'].length > 0){
                        data['data_entries'].forEach(person => {
                            const cardHtml = `
                                <div class="card mb-3 shadow-sm border-start border-success border-4">
                                    <div class="card-body p-3">
                                        <div class="d-flex justify-content-between align-items-center mb-2">
                                            <span class="badge bg-light text-dark border">ID: ${person.cop_id}</span>
                                        </div>
                                        
                                        <h6 class="mb-1 fw-bold">${person.first_name} ${person.last_name}</h6>
                                        <p class="text-muted small mb-0">Middle: ${person.middle_name || 'N/A'}</p>
                                        
                                        <div class="d-flex gap-2 mt-3">
                                            <button class="btn btn-sm btn-outline-danger flex-grow-1" 
                                                    data-action="click->attendees#deleteAttendee" data-id="${person.id}">
                                                <i class="bi bi-trash"></i> Delete
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            `;
                            $(this.mobileContainerTarget).append(cardHtml);
                        });
                    }
                }


            }
            else if (data['Status'] == 'Error') {


            }



        }catch(error){

            console.log(error)
        }
    }
}


app.register('attendees', Attendees)

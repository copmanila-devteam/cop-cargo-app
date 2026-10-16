import {Application, Controller} from'./stimulus.js'


const app = Application.start();

const $ = window.$;

class BookingHistory extends Controller{

    static targets = ["table", 'mobileContainer',
        "tableContainer",
    ]
    static values = {

        entriesUrl: String,
    }

    connect(){

        this.getHistoryData()

    }


    async getHistoryData(){

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

            if (data['status'] == 'success'){
                if ($.fn.DataTable.isDataTable(this.tableTarget)){
                    $(this.tableTarget).DataTable().clear().destroy();
                }
                $(this.mobileContainerTarget).empty()
                

                if (data['data_entries'] && data['data_entries'].length > 0){
                        $(this.tableContainerTarget).find('p').remove()
                        $(this.tableTarget).css('display','table');
                
                    

                        $(this.tableTarget).DataTable({
                            data: data['data_entries'],
                            paging:true,
                            searching: true,
                            info: true,
                            columns: [
                                { data: 'origin'},
                                { data: 'destination'},
                                { data: 'date_time_arrived'},
                                { data: 'service_schedule'},
                                { data: 'vehicle'},
                                { data: 'plate_number'},
                                { data: 'subsidy_amount',
                                    render: (data) => {

                                        return `${data}.00`
                                    }
                                },
                                { data: 'amount_released',
                                     render: (data) => {

                                        return `${data}.00`
                                    }
                                },
                            ]

                        })

                    if (data['data_entries'] && data['data_entries'].length > 0){
                        
                        data['data_entries'].forEach(booking => {
                            const cardHtml = `
                                <div class="card mb-3 shadow-sm border-start border-success border-4">
                                    <div class="card-body p-3">
                                        <div class="d-flex justify-content-between align-items-center mb-2">
                                            <span class="badge bg-light text-dark border">Plate Number: ${booking.plate_number}</span>
                                          
                                        </div>
                                        
                                        <h6 class="mb-1 fw-bold">${booking.service_schedule}</h6>
                                        <p class="text-muted small mb-0">Vehicle: ${booking.vehicle || 'N/A'}</p>
                                        <p class="text-muted small mb-0">Origin: ${booking.origin || 'N/A'}</p>
                                        <p class="text-muted small mb-0">Destination: ${booking.destination || 'N/A'}</p>
                                        <p class="text-muted small mb-0">Time Arrived: ${booking.date_time_arrived || 'N/A'}</p>
                                        <p class="text-muted small mb-0">Subsidy Amount: ${booking.subsidy_amount}.00</p>
                                        <p class="text-muted small mb-0">Amount Released: ${booking.amount_released}.00</p>
                                        
                                      
                                    </div>
                                </div>
                            `;
                            $(this.mobileContainerTarget).append(cardHtml);
                        });
                    }
                    }
                    else{
                    
                        $(this.tableTarget).css('display','none');
                        $(this.tableContainerTarget).addClass('text-center')
                        $(this.tableContainerTarget).append('<p>No data available</p>')
                    
                    }
            }
            else if (data['status'] == 'error') {

            }

        }catch(error){

            console.log(error)
        }
    }
}


app.register('history', BookingHistory)

import {Application, Controller} from'./stimulus.js'





const app = Application.start();



const $ = window.$;



class Vouchers extends Controller{



    static targets = ["table", 'formMessages', 'mobileContainer',

        "tableContainer",

    ]

    static values = {



        entriesUrl: String,

    }





    connect(){



        this.getVouchers()

    }





    

    formatDateTime(dateTimeString) {

                if (!dateTimeString) return 'N/A'

                try {

                    const date = new Date(dateTimeString)

                    return date.toLocaleString('en-US', { 

                        year: 'numeric', 

                        month: 'short', 

                        day: 'numeric',

                        hour: '2-digit',

                        minute: '2-digit'

                    })

                } catch {

                    return dateTimeString

                }

            }

    



    serviceScheduleFormat(data){





        const campusName = data.campus.name;

        const scheduleDay = data.day;

        let timeStr = data.time || "";;

        if (timeStr) {

            const [hours, minutes] = timeStr.split(':');

            let hour = parseInt(hours);

            const ampm = hour >= 12 ? 'PM' : 'AM';

            hour = hour % 12 || 12;

            timeStr = `${hour}:${minutes} ${ampm}`;

        }

        

        const formatsched =`${campusName} | ${scheduleDay} ${timeStr}`.trim();

        return formatsched;

    }



    async getVouchers(){



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

                                {data: 'service_schedule',

                                    render: (data) =>{

                                        



                                        return this.serviceScheduleFormat(data)

                                    }

                                },

                                {data: 'arrival_time',

                                    render: (data) => this.formatDateTime(data)

                                },

                                {data: 'voucher'}

                            ]



                        })



                    



                    if (data['data_entries'] && data['data_entries'].length > 0){

                        

                        data['data_entries'].forEach(voucher => {

                            const cardHtml = `

                                <div class="card mb-3 shadow-sm border-start border-success border-4">

                                    <div class="card-body p-3">

                                        <div class="d-flex justify-content-between align-items-center mb-2">

                                           

                                        </div>

                                        

                                        <h6 class="mb-1 fw-bold">${this.serviceScheduleFormat(voucher.service_schedule)} </h6>

                                        <h3 class="mb-1 fw-bold">${voucher.voucher}</h3>

                                        <p class="text-muted small mb-0">Date & Time Arrived: ${this.formatDateTime(voucher.arrival_time) || 'N/A'}</p>

                                        

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

            else if (data['Status'] == 'Error') {





            }







        }catch(error){



            console.log(error)

        }

    }

}





app.register('vouchers', Vouchers)

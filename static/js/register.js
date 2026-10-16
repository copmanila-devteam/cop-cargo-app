import {Application, Controller} from './stimulus.js'





const app = Application.start()



const $ = window.$;

class Register extends Controller{



    static targets = ['gogroupidErrors', 'emailErrors', 'firstnameErrors','lastnameErrors', 'password1Errors', 'password2Errors', 'container']



    connect() {

        this.toasts = []

    }



    _getCSRFToken() {

        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    }





    addSuccess(message) {

        const title =  "Success!"

        this.addToast("success", title, message)

    }



    addError(message) {

        const title = "Error!"

        this.addToast("danger",title , message)

    }



    addToast(type, title, message) {

        const id = Math.random().toString(36).substring(2, 9)

        const toast = this.createToastElement(id, type, title, message)

        

        this.containerTarget.appendChild(toast)

        

        // Trigger entrance animation

        requestAnimationFrame(() => {

          requestAnimationFrame(() => {

            toast.classList.add("toast-visible")

          })

        })



        // Auto-dismiss after duration

        const timer = setTimeout(() => {

          this.removeToast(id)

        }, this.durationValue)



        this.toasts.push({ id, element: toast, timer })

    }





    removeToast(id) {

        const toastData = this.toasts.find(t => t.id === id)

        if (!toastData) return



        const { element, timer } = toastData

        

        // Clear the auto-dismiss timer

        clearTimeout(timer)



        // Trigger exit animation

        element.classList.remove("toast-visible")



        // Remove from DOM after animation

        setTimeout(() => {

          element.remove()

          this.toasts = this.toasts.filter(t => t.id !== id)

        }, 300)

    }





    createToastElement(id, type, title, message) {

        const isSuccess = type === "success"

        const borderClass = isSuccess ? "border-success" : "border-danger"

        const iconColor = isSuccess ? "text-success" : "text-danger"

        const bgClass = isSuccess ? "bg-success-subtle" : "bg-danger-subtle"



        const toast = document.createElement("div")

        toast.className = `toast-item alert ${bgClass} border-start border-4 ${borderClass} shadow-sm mb-3`

        toast.setAttribute("role", "alert")

        toast.setAttribute("data-register-id", id)



        const iconSvg = isSuccess

          ? `<svg class="${iconColor}" width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">

              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>

            </svg>`

          : `<svg class="${iconColor}" width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">

              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>

            </svg>`



        toast.innerHTML = `

          <div class="d-flex align-items-start">

            <div class="flex-shrink-0">

              ${iconSvg}

            </div>

            <div class="flex-grow-1 ms-3">

              <p class="fw-semibold mb-1 text-dark">${this.escapeHtml(title)}</p>

              <p class="mb-0 small text-secondary">${this.escapeHtml(message)}</p>

            </div>

            <button

              type="button"

              data-action="click->register#closeToast"

              data-register-id-param="${id}"

              class="btn-close ms-3"

              aria-label="Close"

            ></button>

          </div>

        `

        return toast

    }





    closeToast(event) {

        const id = event.params.id

        this.removeToast(id)

      }



    escapeHtml(text) {

        const div = document.createElement("div")

        div.textContent = text

        return div.innerHTML

    }



    async registerLeader(e){

        e.preventDefault()



        const data = {

            go_group_id:$('#id_go_group_id[name="go_group_id"]').val(),

            email: $('#id_email[name="email"]').val(),

            first_name: $('#id_first_name[name="first_name"]').val(),

            last_name:$('#id_last_name[name="last_name"]').val(),

            password1:$('#id_password1[name="password1"]').val(),

            password2:$('#id_password2[name="password2"]').val(),

        }





        try{

            const response = await fetch('/register/',{

                method: "POST",

                headers:{

                    'X-Requested-With':'XMLHttpRequest',

                    'X-CSRFToken': this._getCSRFToken(),

                    'Content-Type':'application/json',



                },

                body:JSON.stringify(data),

            })



            if (!response.ok){

               

              

            }



            const result = await response.json();



            if (result['status'] == 'success'){



                

                this.addSuccess(result['message'])

                setTimeout(()=> window.location.href = result['success_url'], 2000);

            }

            else if (result['status'] == 'error forms'){



                const errorFields = result['messages']

                if (errorFields && errorFields['go_group_id']){

                    errorFields['go_group_id'].forEach((error, i)=>{

                         $(this.gogroupidErrorsTarget).append(`<div class="small text-decoration-none text-danger">${error['message']}</div>`)

                    });   

                    setTimeout(()=> $(this.gogroupidErrorsTarget).children().fadeOut(), 1000)

                }

                if (errorFields && errorFields['email']){

                    errorFields['email'].forEach((error, i)=>{

                         $(this.emailErrorsTarget).append(`<div class="small text-decoration-none text-danger">${error['message']}</div>`)

                    });

                   setTimeout(()=> $(this.emailErrorsTarget).children().fadeOut(), 1000)

                }

                if (errorFields && errorFields['first_name']){

                    errorFields['first_name'].forEach((error, i)=>{

                         $(this.firstnameErrorsTarget).append(`<div class="small text-decoration-none text-danger">${error['message']}</div>`)

                    });

                    setTimeout(()=> $(this.firstnameErrorsTarget).children().fadeOut(), 1000)

                }

                if (errorFields && errorFields['last_name']){

                    errorFields['last_name'].forEach((error, i)=>{

                         $(this.lastnameErrorsTarget).append(`<div class="small text-decoration-none text-danger">${error['message']}</div>`)

                    });

                    setTimeout(()=> $(this.lastnameErrorsTarget).children().fadeOut(), 1000)

                }

                if (errorFields && errorFields['password1']){

                    errorFields['password1'].forEach((error, i)=>{

                         $(this.password1ErrorsTarget).append(`<div class="small text-decoration-none text-danger">${error['message']}</div>`)

                    })

                    setTimeout(()=> $(this.password1ErrorsTarget).children().fadeOut(), 1000)

                }

                if (errorFields && errorFields['password2']){

                    errorFields['password2'].forEach((error, i)=>{

                         $(this.password2ErrorsTarget).append(`<div class="small text-decoration-none text-danger">${error['message']}</div>`)

                    });

                   setTimeout(()=> $(this.password2ErrorsTarget).children().fadeOut(), 1000)

                }

            }

            else if(result['status'] == 'error'){

               

                this.addError(result['message'])



            }



        }catch(errors){

            console.log(errors)



        }

    }





}





app.register('register', Register)

document.addEventListener("DOMContentLoaded", function(){

    console.log("AI Resume Screening System Loaded");

    const openHistory = document.getElementById("openHistory");
    const closeHistory = document.getElementById("closeHistory");
    const historyModal = document.getElementById("historyModal");
    const openApplicantHistory = document.getElementById("openApplicantHistory");
    const closeApplicantHistory = document.getElementById("closeApplicantHistory");
    const applicantHistoryModal = document.getElementById("applicantHistoryModal");

    if (openHistory && closeHistory && historyModal) {
        openHistory.addEventListener("click", function(){
            historyModal.classList.add("open");
            historyModal.setAttribute("aria-hidden", "false");
        });

        closeHistory.addEventListener("click", function(){
            historyModal.classList.remove("open");
            historyModal.setAttribute("aria-hidden", "true");
        });

        historyModal.addEventListener("click", function(event){
            if (event.target === historyModal) {
                historyModal.classList.remove("open");
                historyModal.setAttribute("aria-hidden", "true");
            }
        });
    }

    if (openApplicantHistory && closeApplicantHistory && applicantHistoryModal) {
        openApplicantHistory.addEventListener("click", function(){
            applicantHistoryModal.classList.add("open");
            applicantHistoryModal.setAttribute("aria-hidden", "false");
        });

        closeApplicantHistory.addEventListener("click", function(){
            applicantHistoryModal.classList.remove("open");
            applicantHistoryModal.setAttribute("aria-hidden", "true");
        });

        applicantHistoryModal.addEventListener("click", function(event){
            if (event.target === applicantHistoryModal) {
                applicantHistoryModal.classList.remove("open");
                applicantHistoryModal.setAttribute("aria-hidden", "true");
            }
        });
    }

});


const buttons = document.querySelectorAll(".btn");

buttons.forEach(function(button){

    button.addEventListener("mouseover", function(){

        button.style.transform = "scale(1.05)";

    });

    button.addEventListener("mouseout", function(){

        button.style.transform = "scale(1)";

    });

});
function validateSignInForm(){
	const username = document.getElementById("sign-in-username").value.trim();
    const pass = document.getElementById("sign-in-password").value.trim();
    const error = document.getElementById("error-msg");

    error.textContent = "";
    error.style.color = "red";

    if (username === "") {
      error.textContent = "Username required!";
      return false;
    }

    if (pass === "") {
      error.textContent = "Password required!";
      return false;
    }
	alert("You are good to Go!");
	return true;
}
function validateSignUpForm(){
	const username = document.getElementById("sign-up-username").value.trim();
    const pass = document.getElementById("sign-up-password").value.trim();
	const confirmPass=document.getElementById("sign-up-confirm-password").value.trim();
    const error = document.getElementById("sign-up-error-msg");

    error.textContent = "";
    error.style.color = "red";

    if (username === "") {
      error.textContent = "Username required!";
      return false;
    }
	if(pass===""){
		error.textContent = "Password required!";
		return false;
	}
	if(confirmPass===""){
		error.textContent = "Confirm password required!";
		return false;
	}
    if (pass !== confirmPass) {
      error.textContent = "Passwords didn't match!";
      return false;
    }
	alert("You are good to Go!");
	return true;
}
document.addEventListener("DOMContentLoaded", function () {
  const signInContainer = document.getElementById("sign-in-container");
  const signUpContainer = document.getElementById("sign-up-container");
  const showSignUpBtn = document.getElementById("show-signup");
  const showSignInBtn = document.getElementById("show-signin");
  const signInForm = document.getElementById("login-page-form");
  const signUpForm = document.getElementById("sign-up-page-form");
  // const username=document.getElementById("sign-in-username").value.trim();
  const display=document.getElementById("display-name");
  const name=sessionStorage.getItem("username");
  if(display){
	  display.textContent="HELLO "+name;
  }
  if (signInContainer && signUpContainer && showSignUpBtn && showSignInBtn) {
    showSignUpBtn.addEventListener("click", () => {
      signInContainer.style.display = "none";
      signUpContainer.style.display = "flex";
    });

    showSignInBtn.addEventListener("click", () => {
      signUpContainer.style.display = "none";
      signInContainer.style.display = "flex";
    });
  }

  if (signInForm) {
    signInForm.addEventListener("submit", function (e) {
      e.preventDefault();
	  if (validateSignInForm()){
		  const username=document.getElementById("sign-in-username").value.trim();
		  sessionStorage.setItem("username",username);
		  window.location.replace("patient_dashboard.html");
	  }
    });
  }

  if (signUpForm) {
    signUpForm.addEventListener("submit", function (e) {
      if (!validateSignUpForm()) e.preventDefault();
    });
  }
	const signInInputs = document.querySelectorAll(
	"#sign-in-username, #sign-in-password"
	);
	const signInError = document.getElementById("error-msg");

	if (signInInputs.length && signInError) {
	  signInInputs.forEach(input => {
		input.addEventListener("input", () => {
		  signInError.textContent = "";
		});
	  });
	}
	const signUpInputs = document.querySelectorAll(
	  "#sign-up-username, #sign-up-password, #sign-up-confirm-password"
	);
	const signUpError = document.getElementById("sign-up-error-msg");

	if (signUpInputs.length && signUpError) {
	  signUpInputs.forEach(input => {
		input.addEventListener("input", () => {
		  signUpError.textContent = "";
		});
	  });
	}

  /* ---------- HAMBURGER MENU (THIS WAS NEVER RUNNING BEFORE) ---------- */
  const hamMenu = document.getElementById("hamburger-menu");
  const headerSym = document.getElementById("header-symbol");
  const menuSym = document.getElementById("menu-symbol");

  if (hamMenu && headerSym && menuSym) {
    headerSym.addEventListener("click", () => {
      hamMenu.classList.add("active");
    });

    menuSym.addEventListener("click", () => {
      hamMenu.classList.remove("active");
    });
  }

});

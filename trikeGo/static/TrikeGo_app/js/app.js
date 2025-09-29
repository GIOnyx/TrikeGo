
(function(){
  function openModal() {
    var modal = document.getElementById('login');
    if (!modal) return;
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    var modal = document.getElementById('login');
    if (!modal) return;
    modal.style.display = 'none';
    document.body.style.overflow = '';
    if (history.pushState) {
      var u = new URL(window.location.href);
      u.hash = '';
      history.replaceState(null, '', u.toString());
    }
  }

  function handleHash() {
    if (location.hash === '#login') {
      openModal();
    } else {
      closeModal();
    }
  }

  document.addEventListener('click', function(e){
    var t = e.target;
    if (t.matches('a.login-link')) {
      e.preventDefault();
      openModal();
      history.replaceState(null, '', '#login');
    }
    if (t.matches('.modal-overlay')) {
      e.preventDefault();
      closeModal();
    }
  });

  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape') {
      closeModal();
    }
  });

  window.addEventListener('hashchange', handleHash);
  window.addEventListener('DOMContentLoaded', handleHash);
})();



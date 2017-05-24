if(typeof String.prototype.trim !== 'function') {
  String.prototype.trim = function() {
    return this.replace(/^\s+|\s+$/g, '');
  };
}

$(document).ready(function() {

  var fillContentTab = function(department, timeframe) {

    var formatTopCallTypeInfo = function(topCallType, idx) {
      // Takes an array, where first el is call type, second is
      // count of how many there were in given timeframe
      // Idx is the index into the list
      // Returns an li

      var text = (idx + 1) + ". " + topCallType[0].trim() + " - " + topCallType[1] + ' calls';

      var $el = $('<li>');
      $el.text(text);

      if ((idx + 1) % 2 == 0) {
        $el.addClass('even');
      } else {
        $el.addClass('odd');
      }

      return $el;
    }

    if (typeof topCallTypes[department] == 'undefined') {
      return;
    }

    callTypes = topCallTypes[department][timeframe];


    $callTypesOl = $('.call-types');
    $('.call-types').html('');
    $('.no-calls-of-this-type').hide();

    if (callTypes.length == 0) {
      $('.no-calls-of-this-type').show();
    }

    for(var i = 0; i < callTypes.length; i++) {
      var newEl = formatTopCallTypeInfo(callTypes[i], i);
      $callTypesOl.append(newEl);
    }

  }

  var updateContentTab = function() {
    var department = $('.department-tab.active').attr('id').slice(4);
    var timeframe = $('#data-date-range').val();
    $('.department-tab-content').removeClass('police');
    $('.department-tab-content').removeClass('fire');
    $('.department-tab-content').addClass(department);
    fillContentTab(department, timeframe);
  }

  $('.department-tab').click(function() {
    var $tab = $(this);
    if($tab.hasClass('active')) return;

    $('.department-tab.active').removeClass('active');
    $tab.addClass('active');

    updateContentTab();
  });

  $('#data-date-range').change(updateContentTab);

  // Make browse page rows clickable
  $('#browse-page tbody tr').click(function() {
    window.location.href = $(this).find('.explore-link a').attr('href');
    return false;
  });

  // Activation on the address page
  $('#activated-toggle').click(function() {
    var $toggle = $(this);
    var activated = $toggle.hasClass('activated');

    var action = activated ? '/deactivate' : '/activate';
    var url = window.location.pathname + action;

    $.ajax({
      url: url,
      method: 'POST',
      data: {
        "_csrf_token": csrfToken
      },
      success: function(data) {
        $toggle.removeClass('activated');
        $toggle.removeClass('deactivated');

        $toggle.addClass(data);
      },
      error: function(data) {
        alert('Activation did not succeed. Please try again or refresh the page.');
      }
    })

  });
});


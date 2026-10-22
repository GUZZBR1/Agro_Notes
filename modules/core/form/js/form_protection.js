/**
 * @file
 * Show warning when a user is about to navigate away from an unsaved form.
 */
(function ($, Drupal) {

  'use strict'

  // Track the initial state of forms.
  const initialFormState = {};

  // Track whether a submit was clicked "globally" over all attached DOM, so we
  // can ignore those "onbeforeunload" events and allow form submission.
  let submitWasClicked = false;

  // Check to see if a protected form input has changed.
  const protectedFormInputHasChanged = function() {
    return $('form.form-protected :input').is(function(index, element) {
      if (!element.id || !Object.hasOwn(initialFormState, element.id)) {
        return false;
      }
      return $(this).serialize() !== initialFormState[element.id];
    });
  };

  // Define the Drupal form protection behavior.
  Drupal.behaviors.form_protection = {
    attach: function (context) {

      // Save the initial form state of all input elements.
      $('form.form-protected :input', context).each(function () {
        if (this.id) {
          initialFormState[this.id] = $(this).serialize();
        }
      });

      // Tell onbeforeunload to allow the "submit" event through.
      $('form.form-protected').on('submit', () => {
        submitWasClicked = true;
      });

      // Handle navigation, back button, exit etc.
      window.onbeforeunload = function () {

        // If the form has been changed, and a form submission has not occurred,
        // warn the user that they will lose unsaved changes.
        if (protectedFormInputHasChanged() && !submitWasClicked) {

          // For very old browsers show custom text (modern browsers will ignore
          // this text).
          return Drupal.t('You have unsaved changes.');
        }
      }
    }
  };
})(jQuery, Drupal);

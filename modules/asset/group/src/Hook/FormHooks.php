<?php

declare(strict_types=1);

namespace Drupal\farm_group\Hook;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Form hook implementations for farm_group.
 */
class FormHooks {

  /**
   * Implements hook_form_BASE_FORM_ID_alter().
   */
  #[Hook('form_log_form_alter')]
  public function formLogFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Check if the form has the required group fields.
    if (isset($form['group']) && isset($form['is_group_assignment'])) {

      // Set the visible state of the log.group field.
      // Only display if is_group_assignment is checked.
      $form['group']['#states']['visible'] = [':input[name="is_group_assignment[value]"]' => ['checked' => TRUE]];
    }
  }

}

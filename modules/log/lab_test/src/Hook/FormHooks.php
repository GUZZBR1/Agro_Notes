<?php

declare(strict_types=1);

namespace Drupal\farm_lab_test\Hook;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Form hook implementations for farm_lab_test.
 */
class FormHooks {

  /**
   * Implements hook_form_BASE_FORM_ID_alter().
   */
  #[Hook('form_log_form_alter')]
  public function formLogFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Only show the "Soil texture" field if the lab test type is "soil".
    if (isset($form['lab_test_type']) && isset($form['soil_texture'])) {
      $form['soil_texture']['#states']['visible'] = [':input[name="lab_test_type"]' => ['value' => 'soil']];
    }
  }

}

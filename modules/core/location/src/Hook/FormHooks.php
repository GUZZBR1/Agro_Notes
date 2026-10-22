<?php

declare(strict_types=1);

namespace Drupal\farm_location\Hook;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Form hook implementations for farm_location.
 */
class FormHooks {

  /**
   * Implements hook_form_BASE_FORM_ID_alter().
   */
  #[Hook('form_asset_form_alter')]
  public function formAssetFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Check if the form has the required location fields.
    if (isset($form['intrinsic_geometry']) && isset($form['is_fixed'])) {

      // Set the visible state of the asset.intrinsic_geometry field.
      // Only display if is_fixed is checked.
      $form['intrinsic_geometry']['#states']['visible'] = [':input[name="is_fixed[value]"]' => ['checked' => TRUE]];
    }
  }

}

<?php

declare(strict_types=1);

namespace Drupal\farm_log\Hook;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Form hook implementations for farm_log.
 */
class FormHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_form_FORM_ID_alter().
   */
  #[Hook('form_quantity_delete_multiple_confirm_form_alter')]
  public function formQuantityDeleteMultipleConfirmFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Add a warning to bulk quantity delete confirmation form, to emphasize
    // that the quantity will be deleted from all log revisions.
    $message = $this->t('Warning: Deleting quantities will remove them from all revisions of records that reference them.');
    $form['warning'] = [
      '#type' => 'html_tag',
      '#tag' => 'strong',
      '#value' => $message,
      '#weight' => -10,
    ];
  }

}

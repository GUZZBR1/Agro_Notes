<?php

declare(strict_types=1);

namespace Drupal\farm_comment\Hook;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Form hook implementations for farm_comment.
 */
class FormHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_form_BASE_FORM_ID_alter().
   */
  #[Hook('form_comment_form_alter')]
  public function formCommentFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Change "Save" button to "Save comment".
    if (!empty($form['actions']['submit']['#value'])) {
      $form['actions']['submit']['#value'] = $this->t('Save comment');
    }
  }

}

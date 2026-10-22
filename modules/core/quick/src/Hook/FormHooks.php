<?php

declare(strict_types=1);

namespace Drupal\farm_quick\Hook;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Form hook implementations for farm_quick.
 */
class FormHooks {

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * Implements hook_form_alter().
   */
  #[Hook('form_alter')]
  public function formAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Only alter views_form_ forms.
    if (!str_starts_with($form_id, 'views_form_')) {
      return;
    }
    $target = NULL;
    if (isset($form['header']['asset_bulk_form']['action'])) {
      $target = 'asset_bulk_form';
    }
    if (isset($form['header']['log_bulk_form']['action'])) {
      $target = 'log_bulk_form';
    }

    // Alter action options for the target entity type bulk form.
    if ($target) {

      // Check for disabled quick forms.
      $disabled_quick_forms = $this->entityTypeManager->getStorage('quick_form')->getQuery()->accessCheck(TRUE)->condition('status', FALSE)->execute();
      if (empty($disabled_quick_forms)) {
        return;
      }

      // Remove system actions that end with quick_* for a disabled quick form.
      foreach (array_keys($form['header'][$target]['action']['#options']) as $option_id) {
        if (preg_match("/quick_(.*)/", $option_id, $matches) && in_array($matches[1], $disabled_quick_forms)) {
          unset($form['header'][$target]['action']['#options'][$option_id]);
        }
      }
    }
  }

}

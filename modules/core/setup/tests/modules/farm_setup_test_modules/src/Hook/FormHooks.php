<?php

declare(strict_types=1);

namespace Drupal\farm_setup_test_modules\Hook;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Form hook implementations for farm_setup_test_modules.
 */
class FormHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_form_FORM_ID_alter().
   */
  #[Hook('form_farm_setup_block_form_alter')]
  public function formFarmSetupBlockFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Add checkbox and form validation method to the module setup form so that
    // we can test installing the farm_setup_test module, which adds another
    // setup form that should appear after the modules form.
    if (isset($form['plugin_id']['#value']) && $form['plugin_id']['#value'] == 'modules') {
      $form['install_farm_setup_test'] = [
        '#type' => 'checkbox',
        '#title' => $this->t('Install farm_setup_test module'),
      ];
      $form['#validate'][] = [self::class, 'validateFarmSetupBlockForm'];
    }
  }

  /**
   * Additional validation function for the farm_setup_block_form.
   */
  public static function validateFarmSetupBlockForm($form, FormStateInterface $form_state) {

    // If the install_farm_setup_test box is checked, add farm_setup_test to the
    // list of modules to install.
    if (!empty($form_state->getValue('install_farm_setup_test'))) {
      $modules = $form_state->getValue('modules');
      $modules[] = 'farm_setup_test';
      $form_state->setValue('modules', $modules);
    }
  }

}

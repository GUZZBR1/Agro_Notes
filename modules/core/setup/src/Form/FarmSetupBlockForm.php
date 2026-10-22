<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Form;

use Drupal\Core\Form\FormStateInterface;

/**
 * Setup block form.
 *
 * @ingroup farm
 */
class FarmSetupBlockForm extends FarmSetupForm {

  /**
   * {@inheritdoc}
   */
  public function getFormId() {
    return 'farm_setup_block_form';
  }

  /**
   * {@inheritdoc}
   */
  protected function proceed(FormStateInterface $form_state): void {

    // This performs the same logic as the parent method, but does not perform
    // any redirections. Instead, it saves the next plugin to state so that it
    // is shown next time the block is loaded.
    $next_plugin_id = $this->setupWizard->getNextPluginId($form_state->getValue('plugin_id'));
    $this->setupWizard->setBlockPluginId($next_plugin_id);
    if (is_null($next_plugin_id)) {
      $this->completeMessage();
    }
  }

  /**
   * Batch 'finished' callback that runs after module installation.
   *
   * We need a bit of special logic here to ensure that setup wizard forms from
   * newly installed modules are shown next in the setup wizard block context.
   * We only do this if the module installation batch operation was successful,
   * and the current block plugin state is not NULL (which would indicate that
   * the setup wizard process has already been completed).
   */
  public static function finishInstallModulesBatch($success, $results, $operations) {
    /** @var \Drupal\farm_setup\SetupWizardInterface $wizard */
    $wizard = \Drupal::service('farm_setup.wizard');
    if (!$success || is_null($wizard->getBlockPluginId())) {
      return;
    }
    $next_plugin_id = $wizard->getNextPluginId('modules');
    if (!is_null($next_plugin_id)) {
      $wizard->setBlockPluginId($next_plugin_id);
    }
  }

}

<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Form;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Form\FormBase;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Session\AccountInterface;
use Drupal\farm_setup\SetupFormPluginManager;
use Drupal\farm_setup\SetupWizardInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * Setup form.
 *
 * @ingroup farm
 */
class FarmSetupForm extends FormBase {

  use AutowireTrait;

  public function __construct(
    #[Autowire(service: 'plugin.manager.setup_form')]
    protected SetupFormPluginManager $setupFormPluginManager,
    protected SetupWizardInterface $setupWizard,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function getFormId() {
    return 'farm_setup_form';
  }

  /**
   * Checks access for a specific setup form.
   *
   * @param \Drupal\Core\Session\AccountInterface $account
   *   Run access checks for this account.
   * @param string $plugin_id
   *   The setup form plugin ID.
   *
   * @return \Drupal\Core\Access\AccessResultInterface
   *   The access result.
   */
  public function access(AccountInterface $account, string $plugin_id) {
    return $this->setupFormPluginManager->createInstance($plugin_id)->access($account);
  }

  /**
   * Get the title of the setup form.
   *
   * @param string $plugin_id
   *   The setup form plugin ID.
   *
   * @return string
   *   Quick form title.
   */
  public function getTitle(string $plugin_id) {
    return $this->setupFormPluginManager->createInstance($plugin_id)->getTitle();
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state, ?string $plugin_id = NULL) {

    // Build the setup form.
    $form = $this->setupFormPluginManager->createInstance($plugin_id)->buildForm($form, $form_state);

    // Save the plugin ID for validate/submit.
    $form['plugin_id'] = [
      '#type' => 'value',
      '#value' => $plugin_id,
    ];

    // Submit buttons.
    // If this is the welcome plugin, only show "Continue".
    // Or, if this is the resources plugin, only show "Finish".
    // Otherwise, show "Save and continue" (which submits the form), and "Skip"
    // (which goes to the next form without submitting).
    $form['setup']['actions'] = ['#type' => 'actions'];
    if ($plugin_id == 'welcome') {
      $form['setup']['actions']['submit'] = [
        '#type' => 'submit',
        '#value' => $this->t('Continue'),
        '#submit' => [[$this, 'skipSubmit']],
      ];
    }
    elseif ($plugin_id == 'resources') {
      $form['setup']['actions']['submit'] = [
        '#type' => 'submit',
        '#value' => $this->t('Finish'),
        '#submit' => [[$this, 'skipSubmit']],
      ];
    }
    else {
      $form['setup']['actions']['submit'] = [
        '#type' => 'submit',
        '#value' => $this->t('Save and continue'),
      ];
      $form['setup']['actions']['skip'] = [
        '#type' => 'submit',
        '#value' => $this->t('Skip'),
        // Ignore all validation errors, but preserve the plugin_id value.
        '#limit_validation_errors' => [['plugin_id']],
        '#submit' => [[$this, 'skipSubmit']],
      ];
    }

    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function validateForm(array &$form, FormStateInterface $form_state) {
    $plugin_id = $form_state->getValue('plugin_id');
    $this->setupFormPluginManager->createInstance($plugin_id)->validateForm($form, $form_state);
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state) {
    $this->setupFormPluginManager->createInstance($form_state->getValue('plugin_id'))->submitForm($form, $form_state);
    $this->proceed($form_state);
  }

  /**
   * {@inheritdoc}
   */
  public function skipSubmit(array &$form, FormStateInterface $form_state) {
    $this->proceed($form_state);
  }

  /**
   * Proceed to the next setup form.
   *
   * @param \Drupal\Core\Form\FormStateInterface $form_state
   *   The current state of the form.
   */
  protected function proceed(FormStateInterface $form_state): void {
    $next_plugin_id = $this->setupWizard->getNextPluginId($form_state->getValue('plugin_id'));
    if (!is_null($next_plugin_id)) {
      $form_state->setRedirect('farm.setup.wizard.' . $next_plugin_id);
    }
    else {
      $form_state->setRedirect('<front>');
      $this->completeMessage();
    }
  }

  /**
   * Show a setup completion message.
   */
  protected function completeMessage() {
    $this->messenger()->addStatus($this->t('farmOS setup is complete! Happy record keeping!'));
  }

}

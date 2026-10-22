<?php

declare(strict_types=1);

namespace Drupal\farm_form\Form;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Form\ConfigFormBase;
use Drupal\Core\Form\FormStateInterface;

/**
 * Provides settings form for the farm_form module.
 */
class FormSettingsForm extends ConfigFormbase {

  use AutowireTrait;

  /**
   * Config settings.
   *
   * @var string
   */
  const SETTINGS = 'farm_form.settings';

  /**
   * {@inheritdoc}
   */
  public function getFormId() {
    return 'farm_form_settings';
  }

  /**
   * {@inheritdoc}
   */
  protected function getEditableConfigNames() {
    return [
      static::SETTINGS,
    ];
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state) {
    $config = $this->config(static::SETTINGS);
    $form['enable_form_protection'] = [
      '#type' => 'checkbox',
      '#title' => $this->t('Enable form protection'),
      '#description' => $this->t('Display a warning when users attempt to navigate away from forms with unsaved changes.'),
      '#default_value' => $config->get('enable_form_protection'),
    ];
    return parent::buildForm($form, $form_state);
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state) {
    $this->configFactory->getEditable(static::SETTINGS)
      ->set('enable_form_protection', $form_state->getValue('enable_form_protection'))
      ->save();
    parent::submitForm($form, $form_state);
  }

}

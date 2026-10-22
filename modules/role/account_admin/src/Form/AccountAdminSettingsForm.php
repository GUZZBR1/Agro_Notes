<?php

declare(strict_types=1);

namespace Drupal\farm_account_admin\Form;

use Drupal\Core\Cache\CacheTagsInvalidatorInterface;
use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\Config\TypedConfigManagerInterface;
use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Form\ConfigFormBase;
use Drupal\Core\Form\FormStateInterface;

/**
 * Provides a settings form for the Account Admin Role module.
 */
class AccountAdminSettingsForm extends ConfigFormbase {

  use AutowireTrait;

  /**
   * Config settings.
   *
   * @var string
   */
  const SETTINGS = 'farm_account_admin.settings';

  public function __construct(
    ConfigFactoryInterface $config_factory,
    TypedConfigManagerInterface $typed_config_manager,
    protected CacheTagsInvalidatorInterface $cacheTagsInvalidator,
  ) {
    parent::__construct($config_factory, $typed_config_manager);
  }

  /**
   * {@inheritdoc}
   */
  public function getFormId() {
    return 'farm_account_admin_settings';
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

    $form['allow_peer_role_assignment'] = [
      '#type' => 'checkbox',
      '#title' => $this->t('Allow peer role assignment'),
      '#description' => $this->t('Allow users with the Account Admin role to assign/revoke the Account Admin role.'),
      '#default_value' => $config->get('allow_peer_role_assignment'),
    ];

    return parent::buildForm($form, $form_state);
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state) {
    $this->configFactory->getEditable(static::SETTINGS)
      ->set('allow_peer_role_assignment', $form_state->getValue('allow_peer_role_assignment'))
      ->save();

    // Invalidate the user_role:farm_account_admin cache tag.
    $this->cacheTagsInvalidator->invalidateTags(['user_role:farm_account_admin']);

    parent::submitForm($form, $form_state);
  }

}

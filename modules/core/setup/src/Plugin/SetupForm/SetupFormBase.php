<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Plugin\SetupForm;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Messenger\MessengerTrait;
use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Drupal\Core\Plugin\PluginBase;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Psr\Container\ContainerInterface;

/**
 * Base class for setup forms.
 */
class SetupFormBase extends PluginBase implements SetupFormInterface, ContainerFactoryPluginInterface {

  use MessengerTrait;
  use StringTranslationTrait;

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    return new static(
      $configuration,
      $plugin_id,
      $plugin_definition,
    );
  }

  /**
   * {@inheritdoc}
   */
  public function getFormId() {
    return 'farm_setup_' . $this->getPluginId() . '_form';
  }

  /**
   * {@inheritdoc}
   */
  public function getTitle() {
    return (string) ($this->pluginDefinition['title'] ?? '');
  }

  /**
   * {@inheritdoc}
   */
  public function getTaskTitle() {
    return (string) ($this->pluginDefinition['task_title'] ?? '');
  }

  /**
   * {@inheritdoc}
   */
  public function getDescription() {
    return (string) ($this->pluginDefinition['description'] ?? '');
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state) {
    return [];
  }

  /**
   * {@inheritdoc}
   */
  public function validateForm(array &$form, FormStateInterface $form_state) {
    // Validation is optional.
  }

  /**
   * {@inheritdoc}
   */
  public function submitForm(array &$form, FormStateInterface $form_state) {
    // Submit is optional, but presumably this will be overridden.
  }

  /**
   * {@inheritdoc}
   */
  public function access(AccountInterface $account) {
    return AccessResult::allowed();
  }

}

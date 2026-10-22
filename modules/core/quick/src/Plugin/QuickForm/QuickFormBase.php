<?php

declare(strict_types=1);

namespace Drupal\farm_quick\Plugin\QuickForm;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Messenger\MessengerTrait;
use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Drupal\Core\Plugin\PluginBase;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Base class for quick forms.
 */
class QuickFormBase extends PluginBase implements QuickFormInterface, ContainerFactoryPluginInterface {

  use MessengerTrait;
  use StringTranslationTrait;

  /**
   * The quick form ID.
   *
   * @var string
   */
  protected string $quickId;

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    protected EntityTypeManagerInterface $entityTypeManager,
    protected AccountInterface $currentUser,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition);
  }

  /**
   * {@inheritdoc}
   */
  final public function setQuickId(string $id) {
    return $this->quickId = $id;
  }

  /**
   * {@inheritdoc}
   */
  final public function getQuickId() {
    return $this->quickId ?? $this->getPluginId();
  }

  /**
   * {@inheritdoc}
   */
  public function getFormId() {
    return $this->getQuickId();
  }

  /**
   * {@inheritdoc}
   */
  public function getLabel() {
    return (string) ($this->pluginDefinition['label'] ?? '');
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
  public function getHelpText() {
    return (string) ($this->pluginDefinition['helpText'] ?? '');
  }

  /**
   * {@inheritdoc}
   */
  public function getPermissions() {
    return $this->pluginDefinition['permissions'] ?? [];
  }

  /**
   * {@inheritdoc}
   */
  public function access(AccountInterface $account) {
    $permissions = $this->getPermissions();
    return AccessResult::allowedIfHasPermissions($account, $permissions);
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

}

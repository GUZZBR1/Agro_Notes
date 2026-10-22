<?php

declare(strict_types=1);

namespace Drupal\farm_map\Plugin\Block;

use Drupal\Core\Block\Attribute\Block;
use Drupal\Core\Block\BlockBase;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Drupal\Core\Plugin\PluginDependencyTrait;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * Provides a map block.
 */
#[Block(
  id: 'map_block',
  admin_label: new TranslatableMarkup('Map block'),
)]
class MapBlock extends BlockBase implements ContainerFactoryPluginInterface {

  use PluginDependencyTrait;

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition);
  }

  /**
   * {@inheritdoc}
   */
  public function defaultConfiguration() {
    return [
      'map_type' => 'default',
      'map_behaviors' => [],
    ];
  }

  /**
   * {@inheritdoc}
   */
  public function buildConfigurationForm(array $form, FormStateInterface $form_state) {
    $form = parent::buildConfigurationForm($form, $form_state);

    // Map type.
    $map_types = $this->entityTypeManager->getStorage('map_type')->loadMultiple();
    $map_type_options = array_map(function ($map_type) {
      return $map_type->label();
    }, $map_types);
    $form['map_type'] = [
      '#type' => 'select',
      '#title' => $this->t('Map type'),
      '#options' => $map_type_options,
      '#default_value' => $this->configuration['map_type'],
    ];

    // Map behaviors.
    $map_behaviors = $this->entityTypeManager->getStorage('map_behavior')->loadMultiple();
    $map_behavior_options = array_map(function ($map_behavior) {
      return $map_behavior->label();
    }, $map_behaviors);
    $form['map_behaviors'] = [
      '#type' => 'select',
      '#title' => $this->t('Map behaviors'),
      '#description' => $this->t('Add additional behaviors to the map. This form lists all available behaviors, but be aware that some behaviors may require additional settings that must be provided by modules and will not work properly on their own. Note that behaviors may also be added to maps automatically by modules, even if they are not selected in this list. Using a custom map type is one way to avoid this.'),
      '#options' => $map_behavior_options,
      '#default_value' => $this->configuration['map_behaviors'],
      '#multiple' => TRUE,
    ];

    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function blockSubmit($form, FormStateInterface $form_state) {

    // Save map config values if no errors occurred.
    if (!$form_state->getErrors()) {
      $this->configuration['map_type'] = $form_state->getValue('map_type');
      $this->configuration['map_behaviors'] = array_keys($form_state->getValue('map_behaviors'));
    }
  }

  /**
   * {@inheritdoc}
   */
  public function build() {
    return [
      '#type' => 'farm_map',
      '#map_type' => $this->configuration['map_type'] ?? 'default',
      '#behaviors' => $this->configuration['map_behaviors'] ?? [],
    ];
  }

  /**
   * {@inheritdoc}
   */
  public function calculateDependencies() {

    // Add map type dependencies.
    /** @var \Drupal\farm_map\Entity\MapTypeInterface $map_type */
    $map_type = $this->entityTypeManager->getStorage('map_type')->load($this->configuration['map_type'] ?? 'default');
    $this->addDependencies($map_type->getDependencies());

    // Add map behavior dependencies.
    $map_behaviors = $this->configuration['map_behaviors'] ?? [];
    if (!empty($map_behaviors)) {
      /** @var \Drupal\farm_map\Entity\MapBehaviorInterface $behavior */
      foreach ($this->entityTypeManager->getStorage('map_behavior')->loadMultiple($map_behaviors) as $behavior) {
        $this->addDependencies($behavior->getDependencies());
      }
    }

    return $this->dependencies;
  }

}

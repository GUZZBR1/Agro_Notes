<?php

declare(strict_types=1);

namespace Drupal\farm_map\Event;

use Drupal\Component\EventDispatcher\Event;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\farm_map\Entity\MapTypeInterface;

/**
 * An event that is dispatched before rendering a map on the page.
 */
class MapRenderEvent extends Event {

  const EVENT_NAME = 'map_render_event';

  public function __construct(
    private MapTypeInterface $mapType,
    public array $element,
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * Getter method to get the map target ID.
   *
   * @return string
   *   The map target ID.
   */
  public function getMapTargetId() {
    return $this->element['#attributes']['id'];
  }

  /**
   * Getter method to get the map type being rendered.
   *
   * @return \Drupal\farm_map\Entity\MapTypeInterface
   *   The map type config entity.
   */
  public function getMapType() {
    return $this->mapType;
  }

  /**
   * Getter method for map behaviors.
   *
   * This returns a merged list of map behaviors from both the map type
   * configuration and the map element's #behaviors property.
   *
   * @return string[]
   *   An array of map behavior IDs.
   */
  public function getMapBehaviors() {
    $behaviors = $this->getMapType()->getMapBehaviors();
    if (!empty($this->element['#behaviors'])) {
      $behaviors = array_merge($behaviors, $this->element['#behaviors']);
    }
    return $behaviors;
  }

  /**
   * Add behavior to the map.
   *
   * @param string $behavior_name
   *   The behavior name.
   * @param array $settings
   *   Optional behavior settings that will be added to
   *   drupalSettings.farm_map.behaviors.behavior_name.
   *
   * @throws \Drupal\Component\Plugin\Exception\InvalidPluginDefinitionException
   * @throws \Drupal\Component\Plugin\Exception\PluginNotFoundException
   *
   * @see \Drupal\farm_map\Element\FarmMap
   */
  public function addBehavior(string $behavior_name, array $settings = []) {

    // Load the behavior.
    /** @var \Drupal\farm_map\Entity\MapBehaviorInterface $behavior */
    $behavior = $this->entityTypeManager->getStorage('map_behavior')->load($behavior_name);

    // If the behavior has a library, attach it.
    if (!empty($behavior->getLibrary())) {
      $this->element['#attached']['library'][] = $behavior->getLibrary();
    }

    // Add behavior settings if supplied.
    if (!empty($settings)) {
      $behaviorSettings['behaviors'][$behavior_name] = $settings;
      $this->addSettings($behaviorSettings);
    }
  }

  /**
   * Add settings to the map.
   *
   * These settings will be added to drupalSettings.farm_map.
   *
   * @param array $settings
   *   The settings to be added.
   */
  public function addSettings(array $settings) {
    $existing = [];
    if (!empty($this->element['#attached']['drupalSettings']['farm_map'])) {
      $existing = $this->element['#attached']['drupalSettings']['farm_map'];
    }
    $this->element['#attached']['drupalSettings']['farm_map'] = array_replace_recursive($existing, $settings);
  }

  /**
   * Add cache tags to the render element.
   *
   * @param array $tags
   *   An array of cache tags.
   */
  public function addCacheTags(array $tags) {
    $existing = [];
    if (!empty($this->element['#cache']['tags'])) {
      $existing = $this->element['#cache']['tags'];
    }
    $this->element['#cache']['tags'] = array_unique(array_merge($tags, $existing));
  }

}

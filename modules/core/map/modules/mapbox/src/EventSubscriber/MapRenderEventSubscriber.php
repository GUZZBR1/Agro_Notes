<?php

declare(strict_types=1);

namespace Drupal\farm_map_mapbox\EventSubscriber;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\farm_map\Event\MapRenderEvent;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

/**
 * An event subscriber for the MapRenderEvent.
 *
 * This adds the mapbox behavior and api_key setting to all maps.
 */
class MapRenderEventSubscriber implements EventSubscriberInterface {

  public function __construct(
    private ConfigFactoryInterface $configFactory,
  ) {}

  /**
   * {@inheritdoc}
   */
  public static function getSubscribedEvents(): array {
    return [
      MapRenderEvent::EVENT_NAME => 'onMapRender',
    ];
  }

  /**
   * React to the MapRenderEvent.
   *
   * @param \Drupal\farm_map\Event\MapRenderEvent $event
   *   The MapRenderEvent.
   *
   * @throws \Drupal\Component\Plugin\Exception\InvalidPluginDefinitionException
   * @throws \Drupal\Component\Plugin\Exception\PluginNotFoundException
   */
  public function onMapRender(MapRenderEvent $event) {

    // Get the mapbox api_key.
    $api_key = $this->configFactory->get('farm_map_mapbox.settings')->get('api_key');

    // Set a cache tag on the mapbox settings in case this ever changes.
    // This is added to all maps since the mapbox behavior can be added to all
    // maps.
    $event->addCacheTags(['config:farm_map_mapbox.settings']);

    // If the api key exists, add the mapbox behavior.
    if (!empty($api_key)) {
      $event->addBehavior('mapbox', ['api_key' => $api_key]);
    }
  }

}

<?php

declare(strict_types=1);

namespace Drupal\farm_map\EventSubscriber;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\farm_map\Event\MapRenderEvent;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

/**
 * An event subscriber for the MapRenderEvent.
 *
 * Adds default behaviors to maps.
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
   */
  public function onMapRender(MapRenderEvent $event) {

    // Add the map type cache tags.
    $event->addCacheTags($event->getMapType()->getCacheTags());

    // Include map behaviors defined by the map type.
    $map_behaviors = $event->getMapType()->getMapBehaviors();
    foreach ($map_behaviors as $behavior) {
      $event->addBehavior($behavior);
    }

    // Add the WKT behavior if the render element has WKT.
    if (!empty($event->element['#map_settings']['wkt'])) {
      $event->addBehavior('wkt');
    }

    // Get whether the side panel should be enabled.
    $enable_side_panel = $this->configFactory->get('farm_map.settings')->get('enable_side_panel');

    // Set a cache tag on the map settings to invalidate the cache on changes.
    $event->addCacheTags(['config:farm_map.settings']);

    if ($enable_side_panel) {
      $event->addBehavior('enable_side_panel');
    }
  }

}

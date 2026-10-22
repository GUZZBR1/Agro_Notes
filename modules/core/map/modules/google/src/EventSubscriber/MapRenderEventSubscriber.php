<?php

declare(strict_types=1);

namespace Drupal\farm_map_google\EventSubscriber;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\farm_map\Event\MapRenderEvent;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

/**
 * An event subscriber for the MapRenderEvent.
 *
 * This adds the google behavior and api_key setting to all maps.
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

    // Get the google map tiles api_key.
    $api_key = $this->configFactory->get('farm_map_google.settings')->get('api_key');

    // Set a cache tag on the settings in case this ever changes.
    // This is added to all maps since the google behavior can be added to all
    // maps.
    $event->addCacheTags(['config:farm_map_google.settings']);

    // If the api key exists, add the google behavior.
    if (!empty($api_key)) {
      $event->addBehavior('google', ['api_key' => $api_key]);
    }
  }

}

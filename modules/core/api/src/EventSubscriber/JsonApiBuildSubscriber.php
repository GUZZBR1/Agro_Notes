<?php

declare(strict_types=1);

namespace Drupal\farm_api\EventSubscriber;

use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\jsonapi\ResourceType\ResourceTypeBuildEvent;
use Drupal\jsonapi\ResourceType\ResourceTypeBuildEvents;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

/**
 * JSON API build subscriber for disabling resources.
 */
class JsonApiBuildSubscriber implements EventSubscriberInterface {

  public function __construct(
    protected ModuleHandlerInterface $moduleHandler,
  ) {}

  /**
   * {@inheritdoc}
   */
  public static function getSubscribedEvents(): array {
    $events[ResourceTypeBuildEvents::BUILD][] = ['disableResources'];
    return $events;
  }

  /**
   * Disable resources.
   *
   * @param \Drupal\jsonapi\ResourceType\ResourceTypeBuildEvent $event
   *   The build resource build event.
   */
  public function disableResources(ResourceTypeBuildEvent $event) {
    $allowed_entity_types = $this->moduleHandler->invokeAll('farm_api_allow_resource_types');
    $this->moduleHandler->alter('farm_api_allow_resource_types', $allowed_entity_types);
    $entity_type = explode('--', $event->getResourceTypeName())[0];
    if (!in_array($entity_type, $allowed_entity_types)) {
      $event->disableResourceType();
    }
  }

}

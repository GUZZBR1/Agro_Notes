<?php

declare(strict_types=1);

namespace Drupal\farm_import_csv\EventSubscriber;

use Drupal\Core\Config\ConfigCrudEvent;
use Drupal\Core\Config\ConfigEvents;
use Drupal\Core\Routing\RouteBuilderInterface;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

/**
 * Trigger a route rebuild when CSV importer configuration changes.
 */
class CsvMigrationConfigSubscriber implements EventSubscriberInterface {

  public function __construct(
    protected RouteBuilderInterface $routeBuilder,
  ) {}

  /**
   * {@inheritdoc}
   */
  public static function getSubscribedEvents(): array {
    $events[ConfigEvents::SAVE][] = ['rebuildRouter'];
    $events[ConfigEvents::DELETE][] = ['rebuildRouter'];
    return $events;
  }

  /**
   * Informs the router builder a rebuild is needed when necessary.
   *
   * @param \Drupal\Core\Config\ConfigCrudEvent $event
   *   The Event to process.
   */
  public function rebuildRouter(ConfigCrudEvent $event) {
    $config = $event->getConfig();
    if (str_starts_with($config->getName(), 'migrate_plus.migration.')) {
      $this->routeBuilder->setRebuildNeeded();
    }
  }

}

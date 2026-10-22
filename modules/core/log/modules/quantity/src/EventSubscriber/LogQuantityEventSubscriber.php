<?php

declare(strict_types=1);

namespace Drupal\farm_log_quantity\EventSubscriber;

use Drupal\log\Event\LogEvent;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

/**
 * Subscribe to events related to log quantities.
 */
class LogQuantityEventSubscriber implements EventSubscriberInterface {

  /**
   * {@inheritdoc}
   *
   * @return array
   *   The event names to listen for, and the methods that should be executed.
   */
  public static function getSubscribedEvents(): array {
    return [
      LogEvent::CLONE => 'logClone',
    ];
  }

  /**
   * Perform actions on log clone.
   *
   * @param \Drupal\log\Event\LogEvent $event
   *   The log event.
   */
  public function logClone(LogEvent $event) {

    // Get the log entity from the event.
    $log = $event->log;

    // Bail if the log does not reference any quantities.
    if ($log->get('quantity')->isEmpty()) {
      return;
    }

    // Duplicate each referenced quantity.
    $new_quantities = [];
    /** @var \Drupal\quantity\Entity\QuantityInterface $quantity */
    foreach ($log->get('quantity')->referencedEntities() as $quantity) {
      $duplicate_quantity = $quantity->createDuplicate();
      $new_quantities[] = $duplicate_quantity;
    }

    // Update the log to reference the new duplicated quantities.
    $log->set('quantity', $new_quantities);
  }

}

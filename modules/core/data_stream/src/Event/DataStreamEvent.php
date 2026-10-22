<?php

declare(strict_types=1);

namespace Drupal\data_stream\Event;

use Drupal\Component\EventDispatcher\Event;
use Drupal\data_stream\Entity\DataStreamInterface;

/**
 * Class for data stream events.
 */
class DataStreamEvent extends Event {

  const DATA_RECEIVE = 'data_stream_data_receive';

  public function __construct(
    public DataStreamInterface $dataStream,
    public array $context = [],
  ) {
    $this->context = $context + ['data_stream' => $dataStream];
  }

}

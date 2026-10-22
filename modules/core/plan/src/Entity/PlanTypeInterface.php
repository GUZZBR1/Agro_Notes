<?php

declare(strict_types=1);

namespace Drupal\plan\Entity;

use Drupal\Core\Config\Entity\ConfigEntityInterface;
use Drupal\Core\Entity\EntityDescriptionInterface;
use Drupal\Core\Entity\RevisionableEntityBundleInterface;

/**
 * Provides an interface for defining plan type entities.
 */
interface PlanTypeInterface extends ConfigEntityInterface, EntityDescriptionInterface, RevisionableEntityBundleInterface {

  /**
   * Gets the plan type's workflow ID.
   *
   * Used by the $plan->status field.
   *
   * @return string
   *   The plan type workflow ID.
   */
  public function getWorkflowId();

  /**
   * Sets the workflow ID of the plan type.
   *
   * @param string $workflow_id
   *   The workflow ID.
   *
   * @return $this
   */
  public function setWorkflowId($workflow_id);

}
